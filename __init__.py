#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人格切换插件 - MaiBot插件入口
"""

import sys
import os
import logging

# 将插件目录添加到路径，确保可以导入
sys.path.insert(0, os.path.dirname(__file__))

logger = logging.getLogger("personality_switch_plugin")

try:
    # 尝试导入MaiBot的插件基类
    from maibot.plugin import Plugin as MaiBotPlugin, on_message, MessageContext
    
    # 从我们的plugin.py中导入核心类
    from .plugin import PersonalitySwitchPlugin as CorePlugin
    
    class PersonalitySwitchPlugin(MaiBotPlugin):
        """人格切换插件 - MaiBot适配器"""
        
        def __init__(self):
            super().__init__()
            self.name = "人格切换插件"
            self.version = "9.0.1"
            self.author = "人格切换插件开发者"
            self.description = "支持8个人格切换、热插拔、多场景适配的全功能人格插件"
            
            # 初始化核心插件
            self.core_plugin = CorePlugin()
            logger.info("✅ 人格切换插件已适配MaiBot框架")
        
        @on_message
        async def handle_message(self, ctx: MessageContext):
            """处理消息 - 转发到核心插件"""
            # 这里直接调用核心插件的handle_message方法
            # 注意：我们需要调整参数传递
            await self.core_plugin.handle_message(ctx)
        
        async def plugin_load(self):
            """插件加载时调用"""
            logger.info("人格切换插件正在加载...")
            return True
        
        async def plugin_unload(self):
            """插件卸载时调用"""
            logger.info("人格切换插件正在卸载...")
            return True
    
    # 导出插件类
    plugin = PersonalitySwitchPlugin
    
except ImportError as e:
    logger.error(f"无法导入MaiBot框架: {str(e)}")
    logger.warning("将使用独立模式运行人格切换插件")
    
    # 独立模式
    class PersonalitySwitchPlugin:
        def __init__(self):
            from .plugin import PersonalitySwitchPlugin as CorePlugin
            self.core_plugin = CorePlugin()
            self.name = "人格切换插件"
            self.version = "9.0.1"
    
    plugin = PersonalitySwitchPlugin