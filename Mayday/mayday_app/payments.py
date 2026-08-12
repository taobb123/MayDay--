"""
支付骨架：订单创建、履约、Stripe Checkout（可选）
密钥仅来自 Django settings / 环境变量。
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from .membership import mock_upgrade_membership
from .models import MembershipOrder


def payment_mode() -> dict:
    """供前端展示的支付模式信息。"""
    provider = getattr(settings, 'PAYMENT_PROVIDER', 'mock') or 'mock'
    stripe_ready = bool(getattr(settings, 'STRIPE_SECRET_KEY', ''))
    effective = provider
    note = '演示开通（非真实扣款）'
    if provider == 'stripe':
        if stripe_ready:
            note = 'Stripe Checkout（真实支付通道，请配置成功回调与 Webhook）'
        else:
            effective = 'mock'
            note = '已选 Stripe 但未配置 STRIPE_SECRET_KEY，已降级为演示开通'
    return {
        'configured_provider': provider,
        'effective_provider': effective,
        'stripe_ready': stripe_ready,
        'amount_cents': int(getattr(settings, 'MEMBERSHIP_PRICE_CENTS', 990)),
        'currency': getattr(settings, 'MEMBERSHIP_CURRENCY', 'cny'),
        'days': int(getattr(settings, 'MEMBERSHIP_DAYS', 30)),
        'note': note,
    }


def create_pending_order(user: User, provider: str) -> MembershipOrder:
    return MembershipOrder.objects.create(
        user=user,
        provider=provider,
        status=MembershipOrder.STATUS_PENDING,
        amount_cents=int(getattr(settings, 'MEMBERSHIP_PRICE_CENTS', 990)),
        currency=getattr(settings, 'MEMBERSHIP_CURRENCY', 'cny'),
        days=int(getattr(settings, 'MEMBERSHIP_DAYS', 30)),
    )


def fulfill_order(order: MembershipOrder) -> MembershipOrder:
    """幂等履约：标记已支付并开通会员。"""
    if order.fulfilled and order.status == MembershipOrder.STATUS_PAID:
        return order
    mock_upgrade_membership(order.user, days=order.days)
    order.status = MembershipOrder.STATUS_PAID
    order.fulfilled = True
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'fulfilled', 'paid_at'])
    return order


def start_checkout(user: User, success_url: str, cancel_url: str) -> dict:
    """
    开始结账。
    返回: { mode, order_id, checkout_url?, message }
    """
    mode = payment_mode()
    provider = mode['effective_provider']

    if provider == 'stripe':
        order = create_pending_order(user, MembershipOrder.PROVIDER_STRIPE)
        try:
            checkout_url = _create_stripe_checkout_session(order, success_url, cancel_url)
            return {
                'mode': 'stripe',
                'order_id': order.id,
                'checkout_url': checkout_url,
                'message': '请前往 Stripe 完成支付',
                'payment': mode,
            }
        except Exception as exc:
            order.status = MembershipOrder.STATUS_FAILED
            order.save(update_fields=['status'])
            # 降级 mock，避免阻断演示
            order = create_pending_order(user, MembershipOrder.PROVIDER_MOCK)
            fulfill_order(order)
            return {
                'mode': 'mock',
                'order_id': order.id,
                'message': f'Stripe 创建会话失败，已降级演示开通：{exc}',
                'payment': payment_mode(),
                'degraded': True,
            }

    order = create_pending_order(user, MembershipOrder.PROVIDER_MOCK)
    fulfill_order(order)
    return {
        'mode': 'mock',
        'order_id': order.id,
        'message': f'演示订单已支付并开通会员 {order.days} 天（非真实扣款）',
        'payment': mode,
    }


def _create_stripe_checkout_session(order: MembershipOrder, success_url: str, cancel_url: str) -> str:
    try:
        import stripe
    except ImportError as exc:
        raise RuntimeError('未安装 stripe 包，请 pip install stripe') from exc

    stripe.api_key = settings.STRIPE_SECRET_KEY
    price_id = getattr(settings, 'STRIPE_PRICE_ID', '') or ''

    params = {
        'mode': 'payment',
        'success_url': success_url + ('&' if '?' in success_url else '?') + f'order_id={order.id}',
        'cancel_url': cancel_url,
        'client_reference_id': str(order.id),
        'metadata': {'order_id': str(order.id), 'user_id': str(order.user_id)},
    }
    if price_id:
        params['line_items'] = [{'price': price_id, 'quantity': 1}]
    else:
        params['line_items'] = [{
            'price_data': {
                'currency': order.currency,
                'unit_amount': order.amount_cents,
                'product_data': {'name': f'Mayday 会员 {order.days} 天'},
            },
            'quantity': 1,
        }]

    session = stripe.checkout.Session.create(**params)
    order.external_id = session.id
    order.save(update_fields=['external_id'])
    return session.url


def handle_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    try:
        import stripe
    except ImportError as exc:
        raise RuntimeError('未安装 stripe 包') from exc

    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '') or ''
    if not secret:
        raise RuntimeError('未配置 STRIPE_WEBHOOK_SECRET')

    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id') or session.get('client_reference_id')
        if not order_id:
            return {'ok': False, 'error': 'missing order_id'}
        try:
            order = MembershipOrder.objects.get(id=int(order_id))
        except (MembershipOrder.DoesNotExist, ValueError, TypeError):
            return {'ok': False, 'error': 'order not found'}
        if session.get('id'):
            order.external_id = session['id']
            order.save(update_fields=['external_id'])
        fulfill_order(order)
        return {'ok': True, 'order_id': order.id, 'fulfilled': True}
    return {'ok': True, 'ignored': event['type']}
