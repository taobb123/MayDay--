from django.core.management.base import BaseCommand

from mayday_app.identity import unify_product_account


class Command(BaseCommand):
    help = '把全部歌单/收藏并到本机唯一账号，并停用其它前台账号'

    def handle(self, *args, **options):
        result = unify_product_account()
        self.stdout.write(self.style.SUCCESS(
            f"已统一到 {result['product_user']}："
            f"{result['playlists']} 个歌单，{result['favorites']} 首收藏"
        ))
