/**
 * 播放列表样式检测脚本
 * 在浏览器控制台中运行此脚本，检测样式是否正常加载
 */

(function() {
    console.log('%c=== 播放列表样式检测开始 ===', 'color: #4a90e2; font-size: 16px; font-weight: bold;');
    
    const results = {
        bootstrap: { status: 'unknown', details: '' },
        icons: { status: 'unknown', details: '' },
        table: { status: 'unknown', details: '' },
        buttons: { status: 'unknown', details: '' },
        player: { status: 'unknown', details: '' },
        customStyles: { status: 'unknown', details: '' }
    };
    
    // 1. 检查Bootstrap CSS
    console.log('\n1. 检查 Bootstrap CSS...');
    const bootstrapLink = document.querySelector('link[href*="bootstrap"][rel="stylesheet"]:not([href*="icons"])');
    if (bootstrapLink) {
        const styles = window.getComputedStyle(bootstrapLink);
        results.bootstrap = {
            status: 'success',
            details: `已加载: ${bootstrapLink.href}`
        };
        console.log('✅ Bootstrap CSS 已加载:', bootstrapLink.href);
        
        // 验证样式是否生效
        const testDiv = document.createElement('div');
        testDiv.className = 'btn btn-primary';
        testDiv.style.position = 'absolute';
        testDiv.style.visibility = 'hidden';
        document.body.appendChild(testDiv);
        const computedStyle = window.getComputedStyle(testDiv);
        const hasBootstrap = computedStyle.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                            computedStyle.borderRadius !== '0px';
        document.body.removeChild(testDiv);
        
        if (hasBootstrap) {
            console.log('✅ Bootstrap 样式已生效');
        } else {
            console.warn('⚠️ Bootstrap 样式可能未生效');
            results.bootstrap.status = 'warning';
            results.bootstrap.details += ' (样式可能未生效)';
        }
    } else {
        results.bootstrap = {
            status: 'error',
            details: '未找到 Bootstrap CSS 链接'
        };
        console.error('❌ Bootstrap CSS 未找到');
    }
    
    // 2. 检查Bootstrap Icons
    console.log('\n2. 检查 Bootstrap Icons...');
    const iconsLink = document.querySelector('link[href*="bootstrap-icons"]');
    if (iconsLink) {
        results.icons = {
            status: 'success',
            details: `已加载: ${iconsLink.href}`
        };
        console.log('✅ Bootstrap Icons 已加载:', iconsLink.href);
        
        // 验证图标字体是否加载
        const testIcon = document.createElement('i');
        testIcon.className = 'bi bi-play-fill';
        testIcon.style.position = 'absolute';
        testIcon.style.visibility = 'hidden';
        document.body.appendChild(testIcon);
        const iconStyle = window.getComputedStyle(testIcon, '::before');
        document.body.removeChild(testIcon);
        
        // 检查是否有图标内容
        const hasIcons = testIcon.offsetWidth > 0 || iconStyle.content !== 'none';
        if (hasIcons) {
            console.log('✅ Bootstrap Icons 字体已加载');
        } else {
            console.warn('⚠️ Bootstrap Icons 可能未生效');
            results.icons.status = 'warning';
            results.icons.details += ' (字体可能未加载)';
        }
    } else {
        results.icons = {
            status: 'error',
            details: '未找到 Bootstrap Icons 链接'
        };
        console.error('❌ Bootstrap Icons 未找到');
    }
    
    // 3. 检查表格样式
    console.log('\n3. 检查表格样式...');
    const table = document.querySelector('.table');
    if (table) {
        const styles = window.getComputedStyle(table);
        const hasBootstrapTable = styles.borderCollapse === 'collapse' || 
                                 styles.borderCollapse === 'separate' ||
                                 styles.width !== 'auto';
        
        results.table = {
            status: hasBootstrapTable ? 'success' : 'warning',
            details: `字体: ${styles.fontSize}, 显示: ${styles.display}, 边框: ${styles.borderCollapse}`
        };
        
        if (hasBootstrapTable) {
            console.log('✅ 表格元素存在且样式正常');
            console.log('   字体大小:', styles.fontSize);
            console.log('   显示方式:', styles.display);
            console.log('   边框模式:', styles.borderCollapse);
        } else {
            console.warn('⚠️ 表格元素存在但样式可能异常');
        }
        
        // 检查表头样式
        const th = table.querySelector('th');
        if (th) {
            const thStyles = window.getComputedStyle(th);
            console.log('   表头字体:', thStyles.fontSize);
            console.log('   表头内边距:', thStyles.padding);
            console.log('   表头字重:', thStyles.fontWeight);
        }
    } else {
        results.table = {
            status: 'error',
            details: '未找到 .table 元素'
        };
        console.error('❌ 表格元素未找到');
    }
    
    // 4. 检查播放按钮样式
    console.log('\n4. 检查播放按钮样式...');
    const playButton = document.querySelector('.btn-primary');
    if (playButton) {
        const styles = window.getComputedStyle(playButton);
        const hasBootstrapButton = styles.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                                  styles.borderRadius !== '0px' &&
                                  styles.padding !== '0px';
        
        results.buttons = {
            status: hasBootstrapButton ? 'success' : 'warning',
            details: `背景: ${styles.backgroundColor}, 内边距: ${styles.padding}, 圆角: ${styles.borderRadius}`
        };
        
        if (hasBootstrapButton) {
            console.log('✅ 播放按钮样式正常');
            console.log('   背景色:', styles.backgroundColor);
            console.log('   内边距:', styles.padding);
            console.log('   圆角:', styles.borderRadius);
            console.log('   字体大小:', styles.fontSize);
        } else {
            console.warn('⚠️ 播放按钮样式可能异常');
        }
        
        // 检查按钮图标
        const icon = playButton.querySelector('.bi');
        if (icon) {
            console.log('✅ 按钮图标存在');
        } else {
            console.warn('⚠️ 按钮图标未找到');
        }
    } else {
        results.buttons = {
            status: 'warning',
            details: '未找到 .btn-primary 元素（可能页面中没有播放按钮）'
        };
        console.warn('⚠️ 播放按钮未找到');
    }
    
    // 5. 检查播放器元素和样式
    console.log('\n5. 检查播放器样式...');
    const player = document.getElementById('musicPlayer');
    if (player) {
        const styles = window.getComputedStyle(player);
        const hasActive = player.classList.contains('active');
        
        results.player = {
            status: 'success',
            details: `显示: ${styles.display}, 定位: ${styles.position}, 底部: ${styles.bottom}, 激活: ${hasActive ? '是' : '否'}`
        };
        
        console.log('✅ 播放器元素存在');
        console.log('   显示状态:', styles.display);
        console.log('   定位方式:', styles.position);
        console.log('   底部距离:', styles.bottom);
        console.log('   激活状态:', hasActive ? '是' : '否');
        console.log('   Z-index:', styles.zIndex);
        
        // 检查播放器工具栏
        const toolbar = player.querySelector('.player-toolbar');
        if (toolbar) {
            const toolbarStyles = window.getComputedStyle(toolbar);
            console.log('✅ 播放器工具栏存在');
            console.log('   背景色:', toolbarStyles.backgroundColor);
            console.log('   内边距:', toolbarStyles.padding);
        } else {
            console.warn('⚠️ 播放器工具栏未找到');
        }
        
        // 检查播放器按钮
        const playerBtn = player.querySelector('.player-btn');
        if (playerBtn) {
            const btnStyles = window.getComputedStyle(playerBtn);
            console.log('✅ 播放器按钮存在');
            console.log('   背景色:', btnStyles.backgroundColor);
            console.log('   颜色:', btnStyles.color);
            console.log('   内边距:', btnStyles.padding);
        } else {
            console.warn('⚠️ 播放器按钮未找到');
        }
    } else {
        results.player = {
            status: 'error',
            details: '未找到 #musicPlayer 元素'
        };
        console.error('❌ 播放器元素未找到');
    }
    
    // 6. 检查自定义样式
    console.log('\n6. 检查自定义样式...');
    const styleTag = document.querySelector('style');
    if (styleTag) {
        const styleContent = styleTag.textContent || styleTag.innerHTML;
        const hasPlayerStyle = styleContent.includes('.music-player');
        const hasTableStyle = styleContent.includes('.table');
        const hasButtonStyle = styleContent.includes('.btn-sm');
        
        results.customStyles = {
            status: hasPlayerStyle && hasTableStyle ? 'success' : 'warning',
            details: `播放器样式: ${hasPlayerStyle ? '是' : '否'}, 表格样式: ${hasTableStyle ? '是' : '否'}, 按钮样式: ${hasButtonStyle ? '是' : '否'}`
        };
        
        if (hasPlayerStyle && hasTableStyle) {
            console.log('✅ 自定义样式已加载');
            console.log('   包含播放器样式:', hasPlayerStyle);
            console.log('   包含表格样式:', hasTableStyle);
            console.log('   包含按钮样式:', hasButtonStyle);
        } else {
            console.warn('⚠️ 自定义样式可能不完整');
        }
    } else {
        results.customStyles = {
            status: 'error',
            details: '未找到 <style> 标签'
        };
        console.error('❌ 自定义样式未找到');
    }
    
    // 生成总结报告
    console.log('\n%c=== 检测结果总结 ===', 'color: #4a90e2; font-size: 16px; font-weight: bold;');
    
    const successCount = Object.values(results).filter(r => r.status === 'success').length;
    const warningCount = Object.values(results).filter(r => r.status === 'warning').length;
    const errorCount = Object.values(results).filter(r => r.status === 'error').length;
    
    console.log(`✅ 正常: ${successCount}`);
    console.log(`⚠️ 警告: ${warningCount}`);
    console.log(`❌ 错误: ${errorCount}`);
    
    // 详细结果
    console.log('\n详细结果:');
    Object.entries(results).forEach(([key, value]) => {
        const icon = value.status === 'success' ? '✅' : value.status === 'warning' ? '⚠️' : '❌';
        console.log(`${icon} ${key}: ${value.details}`);
    });
    
    // 返回结果对象供进一步使用
    return results;
})();

