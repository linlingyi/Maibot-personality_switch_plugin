#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人格切换插件 v9.0.1
修复版本：解决botconfig.toml覆盖问题，完整显示8个人格
终极完整版人格切换插件，支持8个人格（名字/滴滴喵/陆尔泠等）、人格热插拔、多场景适配、
智能化交互（意图+情绪识别）、多模态回复（图片+语音）、第三方工具集成、离线模式等全功能
"""

import toml
import json
import sys
import os

# 尝试导入框架适配器
try:
    from framework_adapter import Plugin, on_message, MessageContext
    HAS_FRAMEWORK = True
except ImportError:
    # 如果没有框架适配器，使用通用实现
    HAS_FRAMEWORK = False
    # 定义通用实现
    class Plugin:
        def __init__(self):
            pass
    
    class MessageContext:
        def __init__(self, bot=None, event=None, content="", user_id="", group_id=""):
            self.bot = bot
            self.event = event
            self.content = content
            self.user = type('User', (), {'id': user_id})()
            self.group_id = group_id
        
        async def send(self, message: str):
            print(f"[Bot Reply] {message}")
    
    def on_message(func=None):
        def decorator(f):
            return f
        return decorator if func is None else decorator(func)

import time
import random
import asyncio
import logging
logger = logging.getLogger("personality_switch_plugin")

# 根据提供的路径定位botconfig
BOT_CONFIG_PATH = r"F:\QQRobot\00DMMaibot\LL\MaiBot\config\bot_config.toml"

# 插件中加载专属配置
class YourPlugin:
    def __init__(self):
        # 加载插件专属人格配置（核心）
        self.persona_config_path = "persona_config.toml"
        self.persona_config = self._load_persona_config()
        # 加载全局配置（仅用于非人格相关逻辑）
        self.bot_config = self._load_bot_config()

    def _load_persona_config(self):
        """加载插件专属人格配置"""
        try:
            with open(self.persona_config_path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except FileNotFoundError:
            # 配置文件不存在则初始化
            init_config = {
                "global": {"default_mode": "agent", "force_global": False},
                "user_custom": {}
            }
            with open(self.persona_config_path, "w", encoding="utf-8") as f:
                toml.dump(init_config, f)
            return init_config
        except Exception as e:
            LOGGER.error(f"加载人格配置失败：{e}")
            return {}

    async def switch_persona(self, user_id: str, new_mode: str):
        """切换人格（完全基于专属配置，不受全局影响）"""
        # 1. 更新用户个性化配置
        self.persona_config["user_custom"][user_id] = new_mode
        # 2. 保存专属配置
        with open(self.persona_config_path, "w", encoding="utf-8") as f:
            toml.dump(self.persona_config, f)
        # 3. 后续逻辑读取专属配置（而非全局botconfig）
        # 示例：获取用户当前人格
        current_mode = self.persona_config["user_custom"].get(user_id, self.persona_config["global"]["default_mode"])
        return f"人格切换成功！当前模式：{current_mode}"

def switch_global_personality(personality_name):
    """切换全局人格（覆盖botconfig）- 修复版"""
    # 在函数开头声明全局变量
    global BOT_CONFIG_PATH
    
    try:
        # 验证路径是否存在
        if not os.path.exists(BOT_CONFIG_PATH):
            # 尝试其他可能的路径
            alt_paths = [
                r"F:\QQRobot\00DMMaibot\LL\MaiBot\config\bot_config.toml",
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "bot_config.toml"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "bot_config.toml"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "bot_config.toml"),
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    BOT_CONFIG_PATH = path
                    logger.info(f"找到botconfig.toml: {path}")
                    break
            else:
                logger.error(f"找不到botconfig.toml文件，请检查路径")
                return False
        
        logger.info(f"开始修改botconfig.toml: {BOT_CONFIG_PATH}")
        
        # 读取原有配置
        with open(BOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            bot_config = toml.load(f)
        
        # 备份原配置
        backup_path = BOT_CONFIG_PATH + ".bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            toml.dump(bot_config, f)
        logger.info(f"备份原配置到: {backup_path}")
        
        # 深度搜索并修改人格配置
        def deep_update_config(config, path=""):
            modified = False
            
            if isinstance(config, dict):
                # 检查常见的人格配置字段
                personality_fields = [
                    "personality", "default_personality", "master", "default", 
                    "current_persona", "active_personality", "current_personality"
                ]
                
                for field in personality_fields:
                    if field in config:
                        old_value = config[field]
                        config[field] = personality_name
                        logger.info(f"在路径 {path}.{field} 修改 {old_value} -> {personality_name}")
                        modified = True
                
                # 递归检查子字段
                for key, value in config.items():
                    if deep_update_config(value, f"{path}.{key}"):
                        modified = True
            elif isinstance(config, list):
                # 检查列表中的字典项
                for i, item in enumerate(config):
                    if deep_update_config(item, f"{path}[{i}]"):
                        modified = True
            
            return modified
        
        # 尝试修改现有配置
        modified = deep_update_config(bot_config, "")
        
        # 如果没找到相关字段，直接在最外层添加
        if not modified:
            # 检查是否已经有personality字段
            if "personality" not in bot_config:
                bot_config["personality"] = {}
            
            if isinstance(bot_config["personality"], dict):
                # 检查常见的内层字段
                inner_fields = ["default", "master", "current", "active"]
                for field in inner_fields:
                    if field in bot_config["personality"]:
                        bot_config["personality"][field] = personality_name
                        logger.info(f"在personality.{field}设置人格: {personality_name}")
                        modified = True
                        break
                
                if not modified:
                    # 直接设置default字段
                    bot_config["personality"]["default"] = personality_name
                    logger.info(f"添加personality.default: {personality_name}")
                    modified = True
            else:
                # personality字段不是字典，直接替换
                bot_config["personality"] = personality_name
                logger.info(f"设置personality字段为: {personality_name}")
                modified = True
        
        # 持久化配置
        with open(BOT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            toml.dump(bot_config, f)
        
        # 验证写入
        with open(BOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            verify_config = toml.load(f)
        
        logger.info(f"✅ 全局人格已切换为「{personality_name}」")
        logger.info(f"配置文件已更新: {BOT_CONFIG_PATH}")
        logger.info(f"验证配置: {verify_config}")
        
        return True
    except Exception as e:
        logger.error(f"修改全局人格失败：{str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

import sqlite3
import hashlib
import threading
import re
from typing import Dict, Optional, Any, List, Tuple, Union
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, render_template_string, request, redirect, url_for, session
from functools import wraps
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import base64

# LLM依赖
try:
    from openai import OpenAI
except ImportError:
    raise ImportError("请安装openai库：pip install openai")
try:
    from zhipuai import ZhipuAI
except ImportError:
    print("警告：未安装zhipuai库，ChatGLM模型将无法使用")

# 第三方工具依赖
try:
    from textblob import TextBlob
except ImportError:
    print("警告：未安装textblob，情绪识别降级为关键词匹配")
try:
    import redis
except ImportError:
    print("警告：未安装redis，缓存降级为本地存储")
try:
    import pyttsx3
except ImportError:
    print("警告：未安装pyttsx3，TTS功能禁用")
try:
    import icalendar
    from urllib.request import urlopen
except ImportError:
    print("警告：未安装icalendar，日历工具禁用")
try:
    import requests
except ImportError:
    print("警告：未安装requests，第三方工具（天气/图片生成）禁用")

# 初始化一个基本的日志记录器
LOGGER = logging.getLogger("personality_switch_plugin")
LOGGER.setLevel(logging.INFO)

# 添加控制台处理器（避免NullHandler问题）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
LOGGER.addHandler(console_handler)

# 检查并导入必需依赖
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_APSCHEDULER = True
except ImportError:
    LOGGER.warning("未安装APScheduler，定时任务功能禁用")
    HAS_APSCHEDULER = False
    AsyncIOScheduler = None

try:
    from flask import Flask, render_template_string, request, redirect, url_for, session
    HAS_FLASK = True
except ImportError:
    LOGGER.warning("未安装Flask，Web监控面板禁用")
    HAS_FLASK = False
    Flask = None

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    LOGGER.warning("未安装pandas，数据分析功能禁用")
    HAS_PANDAS = False
    pd = None

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    LOGGER.warning("未安装matplotlib，图表功能禁用")
    HAS_MATPLOTLIB = False
    plt = None

from io import BytesIO, StringIO
import base64

# 尝试导入插件框架
try:
    from maibot.plugin import Plugin, on_message, MessageContext
    HAS_MAIBOT = True
except ImportError:
    LOGGER.warning("未找到maibot，使用兼容模式")
    HAS_MAIBOT = False
    # 创建兼容类
    class Plugin:
        def __init__(self):
            self.name = "PersonalitySwitchPlugin"
    
    class MessageContext:
        def __init__(self, content="", user_id=""):
            self.content = content
            self.user = type('User', (), {'id': user_id})()
        
        async def send(self, message):
            LOGGER.info(f"[Bot Reply] {message}")
            print(f"[Bot Reply] {message}")
        
        async def send_file(self, file_path):
            LOGGER.info(f"[Bot Send File] {file_path}")
            print(f"[Bot Send File] {file_path}")
    
    def on_message(func=None):
        def decorator(f):
            return f
        return decorator if func is None else decorator(func)

# 全局变量
GLOBAL_CURRENT_PERSONALITY: Optional[Dict[str, Any]] = None
CONFIG: Dict[str, Any] = {}
PERSONALITIES: Dict[str, Any] = {}
CUSTOM_PERSONALITIES: Dict[str, Any] = {}  # 自定义人格
DEFAULT_PERSONALITY: Optional[Dict[str, Any]] = None
LLM_CLIENTS: Dict[str, Any] = {}
USER_CONVERSATION_HISTORY: Dict[str, List[Tuple[str, str, str]]] = {}
USER_CONVERSATION_SUMMARY: Dict[str, str] = {}
GLOBAL_SHARED_MEMORY: Dict[str, Any] = {
    "conversations": [], "switch_records": {}, "personality_stats": {}, "persona_mood": {}
}
RANDOM_PERSONALITY_CONFIG: Dict[str, Any] = {}
SCHEDULER: Optional[AsyncIOScheduler] = None
LAST_MESSAGE_TIME: Dict[str, float] = {}
USER_PREFERENCE: Dict[str, Dict[str, int]] = {}
SWITCH_PENDING: Dict[str, Tuple[str, float]] = {}
PERSONA_MOOD: Dict[str, str] = {}  # 人格当前情绪
CURRENT_TOPIC: Dict[str, str] = {}  # 全局话题：{user_id: 话题}
TOPIC_CHAT_COUNT: Dict[str, int] = {}  # 话题聊天轮数：{user_id: 次数}
DB_CONN: Optional[sqlite3.Connection] = None
CACHE_CLIENT: Any = None  # 缓存客户端（Redis/本地字典）
USER_HABITS: Dict[str, Dict[str, List[str]]] = {}  # 用户习惯：{user_id: {high_freq_words: [], reply_length: [], topic_preference: []}}
EMOTION_MODEL: Any = None  # 情绪识别模型

# 提醒相关全局变量
USER_REMINDERS: Dict[str, List[Dict[str, Any]]] = {}  # 用户提醒列表

# 初始化日志记录器（修复版）
def init_logger():
    """初始化日志记录器"""
    global LOGGER
    
    # 如果已经初始化过，直接返回
    if LOGGER.handlers and len(LOGGER.handlers) > 0:
        return LOGGER
    
    # 确保日志记录器存在
    if not LOGGER:
        LOGGER = logging.getLogger("personality_switch_plugin")
    
    # 设置默认日志级别
    LOGGER.setLevel(logging.INFO)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 清除现有处理器，避免重复
    LOGGER.handlers.clear()
    LOGGER.addHandler(console_handler)
    
    return LOGGER

# 确保日志记录器已初始化
LOGGER = init_logger()

# 动态LLM客户端（修改部分）
class DynamicLLMClient:
    def __init__(self, model_config: Dict[str, Any]):
        self.model_type = model_config.get("model_type", "openai")  # 添加默认值
        self.api_base = model_config.get("api_base")
        self.api_key = model_config.get("api_key")
        self.model_name = model_config.get("model_name", "gpt-3.5-turbo")  # 添加默认模型
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 300)
        self.client = self._init_client()

    def _init_client(self):
        if self.model_type == "openai":
            return OpenAI(api_key=self.api_key or "placeholder", base_url=self.api_base)
        elif self.model_type == "chatglm":
            if not self.api_key:
                raise ValueError("ChatGLM需要api_key")
            return ZhipuAI(api_key=self.api_key)
        elif self.model_type == "deepseek":
            return OpenAI(api_key=self.api_key or "placeholder", base_url=self.api_base)
        else:
            # 添加对None的处理
            raise ValueError(f"不支持的模型类型：{self.model_type}（请检查config.toml中的llm.default_model_type配置）")
    
    def generate_reply(self, messages: List[Dict[str, str]]) -> str:
        try:
            if self.model_type in ["openai", "deepseek"]:
                response = self.client.chat.completions.create(
                    model=self.model_name, messages=messages, temperature=self.temperature, max_tokens=self.max_tokens
                )
                return response.choices[0].message.content.strip()
            elif self.model_type == "chatglm":
                response = self.client.chat.completions.create(
                    model=self.model_name, messages=messages, temperature=self.temperature, max_tokens=self.max_tokens
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            LOGGER.error(f"LLM调用失败：{str(e)}")
            return "哎呀，我有点卡壳啦～稍后再聊吧～😣"

# 数据库操作类
class DatabaseManager:
    def __init__(self):
        self.enable = CONFIG["database"]["enable"]
        if not self.enable:
            return
        self.type = CONFIG["database"]["type"]
        if self.type == "sqlite":
            self.conn = sqlite3.connect(CONFIG["database"]["path"], check_same_thread=False)
            self._create_tables()
        elif self.type == "mysql":
            import pymysql
            mysql_config = CONFIG["database"]["mysql_config"]
            self.conn = pymysql.connect(
                host=mysql_config["host"],
                port=mysql_config["port"],
                user=mysql_config["user"],
                password=mysql_config["password"],
                db=mysql_config["db_name"],
                charset="utf8mb4"
            )
            self._create_tables()
        else:
            raise ValueError(f"不支持的数据库类型：{self.type}")
        global DB_CONN
        DB_CONN = self.conn
        LOGGER.info("数据库连接成功")

    def _create_tables(self):
        """创建数据表（包含所有新增功能表）"""
        cursor = self.conn.cursor()
        # 1. 用户对话历史表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            time TEXT NOT NULL,
            persona_name TEXT NOT NULL,
            content TEXT NOT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 2. 用户偏好表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preference (
            user_id TEXT PRIMARY KEY,
            preference_json TEXT NOT NULL
        )
        """)
        # 3. 人格切换记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS persona_switch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            time TEXT NOT NULL,
            persona_name TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 4. 人格活跃度统计表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS persona_stats (
            persona_name TEXT PRIMARY KEY,
            switch_count INTEGER DEFAULT 0
        )
        """)
        # 5. 人格关系表（成长系统）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS persona_relationships (
            persona1 TEXT NOT NULL,
            persona2 TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            interact_count INTEGER DEFAULT 0,
            PRIMARY KEY (persona1, persona2)
        )
        """)
        # 6. 人格成长表（成长系统）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS persona_growth (
            persona_name TEXT PRIMARY KEY,
            interact_count INTEGER DEFAULT 0,
            unlocked TEXT DEFAULT '[]'
        )
        """)
        # 7. 操作日志表（权限系统）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            time TEXT NOT NULL,
            result TEXT NOT NULL
        )
        """)
        # 8. 场景表（多场景适配）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenes (
            scene_name TEXT PRIMARY KEY,
            description TEXT NOT NULL
        )
        """)
        # 9. 用户当前场景表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_current_scene (
            user_id TEXT PRIMARY KEY,
            scene_name TEXT NOT NULL
        )
        """)
        # 10. 场景默认人格表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scene_default_persona (
            scene_name TEXT PRIMARY KEY,
            persona_name TEXT NOT NULL
        )
        """)
        # 11. 场景记忆表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scene_memory (
            scene_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            conversation_json TEXT DEFAULT '[]',
            preference_json TEXT DEFAULT '{}',
            PRIMARY KEY (scene_name, user_id)
        )
        """)
        # 12. 提醒表（新增）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            trigger_time TEXT NOT NULL,
            persona_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 初始化人格活跃度
        for persona_name in PERSONALITIES.keys():
            cursor.execute("SELECT * FROM persona_stats WHERE persona_name = ?", (persona_name,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO persona_stats (persona_name, switch_count) VALUES (?, ?)", (persona_name, 0))
        self.conn.commit()

    def insert_conversation(self, user_id: str, time_str: str, persona_name: str, content: str):
        """插入对话历史"""
        if not self.enable:
            return
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO user_conversation (user_id, time, persona_name, content)
        VALUES (?, ?, ?, ?)
        """, (user_id, time_str, persona_name, content))
        self.conn.commit()

    def get_conversation(self, user_id: str, limit: int = 20) -> List[Tuple[str, str, str]]:
        """获取用户对话历史"""
        if not self.enable:
            return USER_CONVERSATION_HISTORY.get(user_id, [])[:limit]
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT time, persona_name, content FROM user_conversation
        WHERE user_id = ? ORDER BY id DESC LIMIT ?
        """, (user_id, limit))
        results = cursor.fetchall()
        return results[::-1]  # 倒序返回（最新的在最后）

    def update_preference(self, user_id: str, preference: Dict[str, int]):
        """更新用户偏好"""
        if not self.enable:
            USER_PREFERENCE[user_id] = preference
            return
        cursor = self.conn.cursor()
        preference_json = json.dumps(preference, ensure_ascii=False)
        cursor.execute("SELECT * FROM user_preference WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE user_preference SET preference_json = ? WHERE user_id = ?", (preference_json, user_id))
        else:
            cursor.execute("INSERT INTO user_preference (user_id, preference_json) VALUES (?, ?)", (user_id, preference_json))
        self.conn.commit()

    def get_preference(self, user_id: str) -> Dict[str, int]:
        """获取用户偏好"""
        if not self.enable:
            return USER_PREFERENCE.get(user_id, {name: 0 for name in PERSONALITIES.keys()})
        cursor = self.conn.cursor()
        cursor.execute("SELECT preference_json FROM user_preference WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        else:
            preference = {name: 0 for name in PERSONALITIES.keys()}
            self.update_preference(user_id, preference)
            return preference

    def insert_switch_record(self, user_id: str, time_str: str, persona_name: str, trigger_type: str):
        """插入切换记录"""
        if not self.enable:
            if user_id not in GLOBAL_SHARED_MEMORY["switch_records"]:
                GLOBAL_SHARED_MEMORY["switch_records"][user_id] = []
            GLOBAL_SHARED_MEMORY["switch_records"][user_id].append((time_str, persona_name, trigger_type))
            return
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO persona_switch (user_id, time, persona_name, trigger_type)
        VALUES (?, ?, ?, ?)
        """, (user_id, time_str, persona_name, trigger_type))
        # 更新活跃度统计
        cursor.execute("""
        UPDATE persona_stats SET switch_count = switch_count + 1 WHERE persona_name = ?
        """, (persona_name,))
        self.conn.commit()

    def get_switch_records(self, user_id: str, limit: int = 5) -> List[Tuple[str, str, str]]:
        """获取切换记录"""
        if not self.enable:
            records = GLOBAL_SHARED_MEMORY["switch_records"].get(user_id, [])
            return records[-limit:] if records else []
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT time, persona_name, trigger_type FROM persona_switch
        WHERE user_id = ? ORDER BY id DESC LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()

    def get_persona_stats(self) -> Dict[str, int]:
        """获取人格活跃度统计"""
        if not self.enable:
            return GLOBAL_SHARED_MEMORY["personality_stats"]
        cursor = self.conn.cursor()
        cursor.execute("SELECT persona_name, switch_count FROM persona_stats")
        results = cursor.fetchall()
        return {name: count for name, count in results}

    def add_reminder(self, user_id: str, content: str, trigger_time: str, persona_name: str):
        """添加提醒"""
        if not self.enable:
            return None
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO reminders (user_id, content, trigger_time, persona_name)
        VALUES (?, ?, ?, ?)
        """, (user_id, content, trigger_time, persona_name))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_reminders(self, user_id: str, status: str = "pending") -> List[Dict[str, Any]]:
        """获取用户的提醒"""
        if not self.enable:
            return USER_REMINDERS.get(user_id, [])
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT id, content, trigger_time, persona_name, status 
        FROM reminders 
        WHERE user_id = ? AND status = ?
        ORDER BY trigger_time ASC
        """, (user_id, status))
        results = cursor.fetchall()
        return [
            {"id": r[0], "content": r[1], "trigger_time": r[2], 
             "persona_name": r[3], "status": r[4]}
            for r in results
        ]

    def update_reminder_status(self, reminder_id: int, status: str):
        """更新提醒状态"""
        if not self.enable:
            return
        cursor = self.conn.cursor()
        cursor.execute("UPDATE reminders SET status = ? WHERE id = ?", (status, reminder_id))
        self.conn.commit()

    def delete_expired_reminders(self):
        """删除过期的提醒"""
        if not self.enable:
            return
        cursor = self.conn.cursor()
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        cursor.execute("DELETE FROM reminders WHERE trigger_time <= ? AND status = 'pending'", (current_time,))
        deleted_count = cursor.rowcount
        self.conn.commit()
        return deleted_count


# 修改 create_monitor_app 函数，使其返回 login_required 装饰器
def create_monitor_app():
    app = Flask(__name__)
    app.secret_key = "persona_plugin_monitor"
    monitor_config = CONFIG["monitor"]
    username = monitor_config["username"]
    password = monitor_config["password"]

    # 登录验证装饰器 - 在函数内部定义
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "logged_in" not in session:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function
    
    # 登录页面
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            input_user = request.form["username"]
            input_pwd = request.form["password"]
            if input_user == username and input_pwd == password:
                session["logged_in"] = True
                return redirect(url_for("dashboard"))
            else:
                return "用户名或密码错误"
        return """
        <form method="post">
            用户名：<input type="text" name="username"><br>
            密码：<input type="password" name="password"><br>
            <input type="submit" value="登录">
        </form>
        """

    # 仪表盘 - 使用内部定义的 login_required
    @app.route("/")
    @login_required
    def dashboard():
        # 获取活跃度统计
        stats = DB_MANAGER.get_persona_stats() if DB_MANAGER.enable else GLOBAL_SHARED_MEMORY["personality_stats"]
        # 生成柱状图
        if HAS_MATPLOTLIB:
            try:
                plt.rcParams["font.sans-serif"] = ["SimHei"]
                fig, ax = plt.subplots(figsize=(8, 4))
                personas = list(stats.keys())
                counts = list(stats.values())
                ax.bar(personas, counts, color="skyblue")
                ax.set_title("人格活跃度统计")
                ax.set_xlabel("人格名称")
                ax.set_ylabel("切换次数")
                plt.xticks(rotation=45)
                # 保存为base64
                buf = BytesIO()
                plt.tight_layout()
                fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                img_base64 = base64.b64encode(buf.getvalue()).decode()
                plt.close(fig)
            except Exception as e:
                img_base64 = ""
                LOGGER.error(f"生成图表失败：{str(e)}")
        else:
            img_base64 = ""

        # 获取插件状态
        plugin_status = {
            "llm_models": list(LLM_CLIENTS.keys()),
            "active_persona": GLOBAL_CURRENT_PERSONALITY["command"] if GLOBAL_CURRENT_PERSONALITY else "None",
            "user_count": len(USER_PREFERENCE),
            "log_level": CONFIG["log"].get("level", "INFO"),
            "personality_count": len(PERSONALITIES),
            "personality_list": list(PERSONALITIES.keys())
        }

        return render_template_string("""
        <h1>人格切换插件监控面板（v9.0.1）</h1>
        <h2>插件状态</h2>
        <p>当前活跃人格：{{ plugin_status.active_persona }}</p>
        <p>加载的LLM模型：{{ plugin_status.llm_models | join(', ') }}</p>
        <p>用户数：{{ plugin_status.user_count }}</p>
        <p>日志级别：{{ plugin_status.log_level }}</p>
        <p>人格数量：{{ plugin_status.personality_count }}</p>
        <p>人格列表：{{ plugin_status.personality_list | join(', ') }}</p>
        <h2>人格活跃度统计</h2>
        {% if img_base64 %}
        <img src="data:image/png;base64,{{ img_base64 }}" alt="活跃度统计">
        {% else %}
        <p>图表生成失败（matplotlib未安装）</p>
        {% endif %}
        <h2>操作</h2>
        <a href="/backup">手动备份数据</a><br>
        <a href="/reminders">查看提醒</a><br>
        <a href="/logout">退出登录</a>
        """, plugin_status=plugin_status, img_base64=img_base64)

    # 备份数据
    @app.route("/backup")
    @login_required
    def backup():
        plugin._auto_backup()
        return "备份完成！<a href='/'>返回仪表盘</a>"

    # 查看提醒
    @app.route("/reminders")
    @login_required
    def view_reminders():
        if not DB_MANAGER.enable:
            return "数据库未启用，无法查看提醒"
        
        reminders = []
        cursor = DB_MANAGER.conn.cursor()
        cursor.execute("""
        SELECT user_id, content, trigger_time, persona_name, status 
        FROM reminders 
        ORDER BY trigger_time DESC 
        LIMIT 50
        """)
        for row in cursor.fetchall():
            reminders.append({
                "user_id": row[0],
                "content": row[1],
                "trigger_time": row[2],
                "persona_name": row[3],
                "status": row[4]
            })
        
        return render_template_string("""
        <h1>提醒列表</h1>
        <table border="1">
            <tr>
                <th>用户ID</th>
                <th>内容</th>
                <th>触发时间</th>
                <th>人格</th>
                <th>状态</th>
            </tr>
            {% for r in reminders %}
            <tr>
                <td>{{ r.user_id }}</td>
                <td>{{ r.content }}</td>
                <td>{{ r.trigger_time }}</td>
                <td>{{ r.persona_name }}</td>
                <td>{{ r.status }}</td>
            </tr>
            {% endfor %}
        </table>
        <br>
        <a href="/">返回仪表盘</a>
        """, reminders=reminders)

    # 退出登录
    @app.route("/logout")
    def logout():
        session.pop("logged_in", None)
        return redirect(url_for("login"))

    return app

def _init_web_config(self):
    """初始化可视化配置工具（Web端修改config.toml）"""
    if not CONFIG.get("web_config", {}).get("enable", False):
        return
    
    # 创建独立的Flask应用，避免与监控面板冲突
    if not HAS_FLASK:
        LOGGER.warning("Flask未安装，可视化配置工具禁用")
        return
    
    web_app = Flask(__name__)
    web_app.secret_key = "persona_web_config_secret"
    
    # 简单的登录检查函数
    def check_login():
        if not session.get("logged_in"):
            return False
        return True
    
    # 登录页面
    @web_app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            # 使用监控面板的用户名密码
            if (username == CONFIG["monitor"]["username"] and 
                password == CONFIG["monitor"]["password"]):
                session["logged_in"] = True
                return redirect(url_for("config_home"))
            return "用户名或密码错误"
        
        return '''
        <h2>可视化配置工具登录</h2>
        <form method="post">
            用户名：<input type="text" name="username"><br>
            密码：<input type="password" name="password"><br>
            <input type="submit" value="登录">
        </form>
        '''
    
    # 配置主页 - 需要登录
    @web_app.route("/")
    def config_home():
        if not check_login():
            return redirect(url_for("login"))
        
        # 获取插件状态
        plugin_status = {
            "personality_count": len(PERSONALITIES),
            "active_persona": GLOBAL_CURRENT_PERSONALITY["command"] if GLOBAL_CURRENT_PERSONALITY else "None",
            "database_enabled": CONFIG["database"]["enable"],
            "cache_enabled": CONFIG["cache"]["enable"]
        }
        
        return f'''
        <h1>人格切换插件可视化配置工具 v9.0.1</h1>
        <h2>插件状态</h2>
        <ul>
            <li>人格数量：{plugin_status['personality_count']}</li>
            <li>当前活跃人格：{plugin_status['active_persona']}</li>
            <li>数据库状态：{'已启用' if plugin_status['database_enabled'] else '已禁用'}</li>
            <li>缓存状态：{'已启用' if plugin_status['cache_enabled'] else '已禁用'}</li>
        </ul>
        <h2>配置选项</h2>
        <ul>
            <li><a href="/personalities">人格配置</a></li>
            <li><a href="/system">系统配置</a></li>
            <li><a href="/logout">退出登录</a></li>
        </ul>
        '''
    
    # 人格配置页面
    @web_app.route("/personalities", methods=["GET", "POST"])
    def personalities_config():
        if not check_login():
            return redirect(url_for("login"))
        
        if request.method == "POST":
            # 保存配置
            try:
                for persona_name in PERSONALITIES.keys():
                    reply_style = request.form.get(f"{persona_name}_reply_style", "").strip()
                    if reply_style:
                        PERSONALITIES[persona_name]["reply_style"] = reply_style
                
                # 保存到config.toml
                with open(os.path.join(os.path.dirname(__file__), "config.toml"), "w", encoding="utf-8") as f:
                    toml.dump(CONFIG, f)
                
                return '''
                <script>
                    alert("配置已保存！");
                    window.location.href = "/personalities";
                </script>
                '''
            except Exception as e:
                return f"保存失败：{str(e)}<br><a href='/personalities'>返回</a>"
        
        # 显示当前配置
        form_html = '''
        <h2>人格配置</h2>
        <form method="post">
        '''
        for persona_name, persona_data in PERSONALITIES.items():
            reply_style = persona_data.get("reply_style", "")
            personality_desc = persona_data.get("personality_desc", "")
            form_html += f'''
            <div style="border:1px solid #ccc; padding:15px; margin-bottom:15px; border-radius:5px;">
                <h3>{persona_name}</h3>
                <div>
                    <strong>人格描述：</strong><br>
                    <textarea name="{persona_name}_personality_desc" rows="3" cols="80" readonly>{personality_desc}</textarea>
                </div>
                <div>
                    <strong>回复风格：</strong><br>
                    <textarea name="{persona_name}_reply_style" rows="4" cols="80">{reply_style}</textarea>
                </div>
            </div>
            '''
        
        form_html += '''
        <input type="submit" value="保存配置">
        <a href="/" style="margin-left:20px;">返回主页</a>
        </form>
        '''
        
        return form_html
    
    # 系统配置页面
    @web_app.route("/system", methods=["GET", "POST"])
    def system_config():
        if not check_login():
            return redirect(url_for("login"))
        
        if request.method == "POST":
            try:
                # 更新LLM配置
                llm_config = CONFIG["llm"]
                llm_config["temperature"] = float(request.form.get("temperature", 0.7))
                llm_config["max_tokens"] = int(request.form.get("max_tokens", 300))
                
                # 更新缓存配置
                cache_config = CONFIG["cache"]
                cache_config["enable"] = request.form.get("cache_enable") == "on"
                cache_config["cache_expire"] = int(request.form.get("cache_expire", 3600))
                
                # 保存到config.toml
                with open(os.path.join(os.path.dirname(__file__), "config.toml"), "w", encoding="utf-8") as f:
                    toml.dump(CONFIG, f)
                
                return '''
                <script>
                    alert("系统配置已保存！");
                    window.location.href = "/system";
                </script>
                '''
            except Exception as e:
                return f"保存失败：{str(e)}<br><a href='/system'>返回</a>"
        
        # 显示当前系统配置
        llm_config = CONFIG["llm"]
        cache_config = CONFIG["cache"]
        
        return f'''
        <h2>系统配置</h2>
        <form method="post">
            <h3>LLM配置</h3>
            <div>
                <label>温度（temperature）：</label>
                <input type="number" name="temperature" step="0.1" min="0" max="2" value="{llm_config.get('temperature', 0.7)}">
                <small>值越高回复越随机，值越低回复越确定</small>
            </div>
            <div>
                <label>最大令牌数（max_tokens）：</label>
                <input type="number" name="max_tokens" min="50" max="2000" value="{llm_config.get('max_tokens', 300)}">
                <small>控制回复的最大长度</small>
            </div>
            
            <h3>缓存配置</h3>
            <div>
                <label>
                    <input type="checkbox" name="cache_enable" {'checked' if cache_config.get('enable', True) else ''}>
                    启用缓存
                </label>
            </div>
            <div>
                <label>缓存过期时间（秒）：</label>
                <input type="number" name="cache_expire" min="60" max="86400" value="{cache_config.get('cache_expire', 3600)}">
            </div>
            
            <br>
            <input type="submit" value="保存配置">
            <a href="/" style="margin-left:20px;">返回主页</a>
        </form>
        '''
    
    # 退出登录
    @web_app.route("/logout")
    def logout():
        session.pop("logged_in", None)
        return redirect(url_for("login"))
    
    # 独立线程启动Web配置工具
    def run_web_app():
        try:
            web_app.run(
                host=CONFIG["web_config"]["host"],
                port=CONFIG["web_config"]["port"],
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            LOGGER.error(f"Web配置工具启动失败：{str(e)}")
    
    web_thread = threading.Thread(target=run_web_app, daemon=True)
    web_thread.start()
    LOGGER.info(f"可视化配置工具已启动：http://{CONFIG['web_config']['host']}:{CONFIG['web_config']['port']}")
    
    
# 核心插件类
class PersonalitySwitchPlugin(Plugin):
    def __init__(self):
        super().__init__()
        # 设置高优先级
        self.priority = 999
        self._load_config()
        self._init_global_vars()
        self._init_llm_clients()
        self._init_database()  # 初始化数据库
        self._init_scheduler()
        self._init_reminder_scheduler()  # 初始化提醒调度器
        self._load_backup()
        self._init_intelligence()  # 智能化模块（意图+情绪+学习）
        self._init_cache()  # 智能缓存
        self._init_tools()  # 第三方工具
        self._init_multimodal()  # 多模态交互
        self._init_offline_mode()  # 离线模式
        self._init_permission()  # 权限管理
        self._init_persona_growth()  # 人格成长系统
        self._init_scenes()  # 多场景适配
        self._init_monitor_app()  # 监控面板
        self._init_web_config()  # 可视化配置工具
        LOGGER.info(f"插件初始化完成（V9.0.1 全优化集成），已加载 {len(PERSONALITIES)} 个人格")

    def _load_config(self):
        """加载配置文件（包含8个人格配置）"""
        global CONFIG, PERSONALITIES, RANDOM_PERSONALITY_CONFIG
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在：{config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            CONFIG = toml.load(f)
        PERSONALITIES = CONFIG.get("personalities", {})
        RANDOM_PERSONALITY_CONFIG = CONFIG.get("random_personality", {})
        
        # 验证人格加载
        LOGGER.info(f"✅ 已加载 {len(PERSONALITIES)} 个人格：{list(PERSONALITIES.keys())}")
        
        if len(PERSONALITIES) != 8:
            LOGGER.warning(f"⚠ 预期8个人格，实际加载了{len(PERSONALITIES)}个")

    def _init_global_vars(self):
        """初始化全局变量"""
        global GLOBAL_CURRENT_PERSONALITY, DEFAULT_PERSONALITY, PERSONA_MOOD
        DEFAULT_PERSONALITY = PERSONALITIES.get("名字")
        GLOBAL_CURRENT_PERSONALITY = DEFAULT_PERSONALITY or next(iter(PERSONALITIES.values()))
        # 初始化人格情绪
        PERSONA_MOOD = {name: p.get("default_mood", "平静") for name, p in PERSONALITIES.items()}
        GLOBAL_SHARED_MEMORY["persona_mood"] = PERSONA_MOOD
        # 初始化用户习惯
        global USER_HABITS
        USER_HABITS = {}
        # 初始化提醒
        global USER_REMINDERS
        USER_REMINDERS = {}

    def _init_llm_clients(self):
        """初始化动态LLM客户端池：全局默认+人格专属"""
        global LLM_CLIENTS
        default_config = CONFIG.get("llm", {})
        LLM_CLIENTS["default"] = DynamicLLMClient({
            "model_type": default_config.get("default_model_type"),
            "api_base": default_config.get("default_api_base"),
            "api_key": default_config.get("default_api_key"),
            "model_name": default_config.get("default_model_name"),
            "temperature": default_config.get("temperature"),
            "max_tokens": default_config.get("max_tokens")
        })
        # 人格专属模型
        persona_models = default_config.get("personality_models", {})
        for persona_name, model_config in persona_models.items():
            if persona_name in PERSONALITIES:
                LLM_CLIENTS[persona_name] = DynamicLLMClient(model_config)
                LOGGER.info(f"为{persona_name}初始化专属模型：{model_config.get('model_type')}")

    def _init_database(self):
        """初始化数据库"""
        global DB_MANAGER
        DB_MANAGER = DatabaseManager()
    
    # ==================== 定时任务系统 ====================
    def _init_scheduler(self):
        """初始化定时任务：随机人格+自动备份"""
        global SCHEDULER
        if not HAS_APSCHEDULER:
            LOGGER.warning("APScheduler未安装，定时任务禁用")
            return
        
        SCHEDULER = AsyncIOScheduler()

        # 随机人格触发器
        if RANDOM_PERSONALITY_CONFIG.get("enable"):
            from apscheduler.triggers.interval import IntervalTrigger
            
            def random_interval():
                min_sec = RANDOM_PERSONALITY_CONFIG["trigger_interval_min"] * 60
                max_sec = RANDOM_PERSONALITY_CONFIG["trigger_interval_max"] * 60
                return random.randint(min_sec, max_sec)
            
            interval_seconds = random_interval()
            trigger = IntervalTrigger(seconds=interval_seconds)
            
            SCHEDULER.add_job(
                self._random_personality_trigger,
                trigger=trigger,
                id="random_persona",
                replace_existing=True
            )
            LOGGER.info(f"随机人格触发已启用，初始间隔：{interval_seconds}秒")

        # 自动备份任务
        if CONFIG.get("backup", {}).get("enable"):
            from apscheduler.triggers.interval import IntervalTrigger
            
            backup_interval = CONFIG["backup"]["interval"] * 3600  # 小时转秒
            trigger = IntervalTrigger(seconds=backup_interval)
            
            SCHEDULER.add_job(
                self._auto_backup,
                trigger=trigger,
                id="auto_backup",
                replace_existing=True
            )
            LOGGER.info(f"自动备份已启用，间隔：{CONFIG['backup']['interval']}小时")

        # 启动调度器
        try:
            SCHEDULER.start()
            LOGGER.info("定时任务调度器已启动")
        except Exception as e:
            LOGGER.error(f"定时任务启动失败：{str(e)}")

    def _init_reminder_scheduler(self):
        """初始化提醒调度器"""
        global SCHEDULER
        
        if not HAS_APSCHEDULER:
            LOGGER.warning("APScheduler未安装，提醒功能禁用")
            return
        
        # 如果调度器未初始化，创建新的
        if SCHEDULER is None:
            SCHEDULER = AsyncIOScheduler()
        
        # 添加提醒清理任务（每10分钟检查一次过期的提醒）
        from apscheduler.triggers.interval import IntervalTrigger
        SCHEDULER.add_job(
            self._clean_expired_reminders,
            trigger=IntervalTrigger(seconds=600),
            id="clean_reminders",
            replace_existing=True
        )
        
        # 从数据库加载待处理的提醒
        if DB_MANAGER.enable:
            try:
                cursor = DB_MANAGER.conn.cursor()
                cursor.execute("""
                SELECT id, user_id, content, trigger_time, persona_name 
                FROM reminders 
                WHERE status = 'pending' AND trigger_time > ?
                """, (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),))
                
                for row in cursor.fetchall():
                    reminder_id, user_id, content, trigger_time, persona_name = row
                    
                    # 计算延迟时间
                    trigger_timestamp = time.mktime(time.strptime(trigger_time, "%Y-%m-%d %H:%M:%S"))
                    delay_seconds = max(0, trigger_timestamp - time.time())
                    
                    if delay_seconds > 0 and delay_seconds <= 7 * 24 * 3600:  # 7天内
                        # 添加定时任务
                        job_id = f"reminder_{reminder_id}"
                        
                        async def send_reminder(rid=reminder_id, uid=user_id, c=content, pn=persona_name):
                            await self._send_reminder_notification(rid, uid, c, pn)
                        
                        SCHEDULER.add_job(
                            send_reminder,
                            'date',
                            run_date=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(trigger_timestamp)),
                            id=job_id,
                            replace_existing=True
                        )
                        
                        LOGGER.debug(f"已加载待处理提醒：ID={reminder_id}, 用户={user_id}, 时间={trigger_time}")
            except Exception as e:
                LOGGER.error(f"加载待处理提醒失败：{str(e)}")
        
        LOGGER.info("提醒调度器已初始化")

    def _random_personality_trigger(self):
        """随机人格切换触发器"""
        if not PERSONALITIES:
            return
    
        # 获取所有可切换的人格（排除当前人格）
        current_persona = GLOBAL_CURRENT_PERSONALITY["command"] if GLOBAL_CURRENT_PERSONALITY else None
        available_personas = [p for p in PERSONALITIES.keys() if p != current_persona]
    
        if not available_personas:
            return
    
        # 随机选择一个人格
        random_persona = random.choice(available_personas)
        old_persona = GLOBAL_CURRENT_PERSONALITY
        GLOBAL_CURRENT_PERSONALITY = PERSONALITIES[random_persona]
    
        # 记录切换
        LOGGER.info(f"随机人格切换：{old_persona['command'] if old_persona else 'None'} -> {random_persona}")
    
        # 更新全局记忆
        GLOBAL_SHARED_MEMORY.setdefault("random_switches", []).append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "from": old_persona["command"] if old_persona else None,
            "to": random_persona
        })
    
        # 如果启用了数据库，记录到数据库
        if DB_MANAGER and DB_MANAGER.enable:
            try:
                cursor = DB_MANAGER.conn.cursor()
                cursor.execute("""
                INSERT INTO persona_switch (user_id, time, persona_name, trigger_type)
                VALUES (?, ?, ?, ?)
                """, ("system", time.strftime("%Y-%m-%d %H:%M:%S"), random_persona, "random"))
                DB_MANAGER.conn.commit()
            except Exception as e:
                LOGGER.error(f"记录随机切换到数据库失败：{str(e)}")
    
        # 设置下一次随机触发的时间
        if SCHEDULER and RANDOM_PERSONALITY_CONFIG.get("enable"):
            from apscheduler.triggers.interval import IntervalTrigger
            interval_seconds = random.randint(
                RANDOM_PERSONALITY_CONFIG["trigger_interval_min"] * 60,
                RANDOM_PERSONALITY_CONFIG["trigger_interval_max"] * 60
            )
        
            # 更新随机人格任务的下次触发时间
            job = SCHEDULER.get_job("random_persona")
            if job:
                trigger = IntervalTrigger(seconds=interval_seconds)
                job.reschedule(trigger)
                LOGGER.debug(f"更新随机人格下次触发间隔：{interval_seconds}秒")

    # ==================== 提醒功能 ====================
    def _parse_reminder_time(self, time_str: str) -> Optional[Dict[str, Any]]:
        """解析提醒时间字符串，支持多种格式"""
        try:
            # 清理输入
            time_str = time_str.strip().lower()
            
            # 支持的格式：
            # 1. 晚上/明天晚上/后天晚上
            # 2. X天后 (如：3天后)
            # 3. X小时后 (如：2小时后)
            # 4. 具体时间 (如：20:30, 明天20:30)
            
            now = time.localtime()
            current_year = now.tm_year
            current_month = now.tm_mon
            current_day = now.tm_mday
            
            # 晚上（默认为20:00）
            if "晚上" in time_str or "傍晚" in time_str:
                hour, minute = 20, 0
                days_offset = 0
                
                if "明天" in time_str:
                    days_offset = 1
                elif "后天" in time_str:
                    days_offset = 2
                elif "大后天" in time_str:
                    days_offset = 3
                
                reminder_time = time.mktime((
                    current_year, current_month, current_day + days_offset,
                    hour, minute, 0, 0, 0, -1
                ))
                
                day_prefix = "明天" if days_offset == 1 else "后天" if days_offset == 2 else "大后天" if days_offset == 3 else "今天"
                return {
                    "timestamp": reminder_time,
                    "display": f"{day_prefix}晚上{hour}:{minute:02d}"
                }
            
            # X天后
            elif "天后" in time_str:
                match = re.search(r'(\d+)\s*天后', time_str)
                if match:
                    days_offset = int(match.group(1))
                    if days_offset > 7:
                        return None  # 超过7天不支持
                    
                    # 默认晚上20:00
                    hour, minute = 20, 0
                    reminder_time = time.mktime((
                        current_year, current_month, current_day + days_offset,
                        hour, minute, 0, 0, 0, -1
                    ))
                    
                    return {
                        "timestamp": reminder_time,
                        "display": f"{days_offset}天后{hour}:{minute:02d}"
                    }
            
            # X小时后
            elif "小时后" in time_str:
                match = re.search(r'(\d+)\s*小时后', time_str)
                if match:
                    hours_offset = int(match.group(1))
                    current_hour = now.tm_hour
                    current_min = now.tm_min
                    
                    total_minutes = current_hour * 60 + current_min + hours_offset * 60
                    target_hour = (total_minutes // 60) % 24
                    target_min = total_minutes % 60
                    days_offset = total_minutes // (24 * 60)
                    
                    reminder_time = time.mktime((
                        current_year, current_month, current_day + days_offset,
                        target_hour, target_min, 0, 0, 0, -1
                    ))
                    
                    return {
                        "timestamp": reminder_time,
                        "display": f"{hours_offset}小时后({target_hour}:{target_min:02d})"
                    }
            
            # 具体时间 (如：20:30)
            elif ":" in time_str:
                match = re.search(r'(\d{1,2}):(\d{2})', time_str)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    days_offset = 0
                    
                    if "明天" in time_str:
                        days_offset = 1
                    elif "后天" in time_str:
                        days_offset = 2
                    elif "大后天" in time_str:
                        days_offset = 3
                    
                    reminder_time = time.mktime((
                        current_year, current_month, current_day + days_offset,
                        hour, minute, 0, 0, 0, -1
                    ))
                    
                    day_prefix = "明天" if days_offset == 1 else "后天" if days_offset == 2 else "大后天" if days_offset == 3 else "今天"
                    return {
                        "timestamp": reminder_time,
                        "display": f"{day_prefix}{hour}:{minute:02d}"
                    }
            
            return None
        except Exception as e:
            LOGGER.error(f"解析提醒时间失败：{str(e)}")
            return None

    async def _add_reminder(self, user_id: str, message: str, ctx: MessageContext):
        """添加提醒"""
        # 解析消息格式：名字提醒我晚上看天气预报
        # 或者：/名字 提醒我3天后看比赛
        # 或者：/名字 提醒我明天20:30看电视
        
        # 提取提醒内容和时间
        pattern = r'(?:提醒我|提醒)(.+?)(?:在|到|的?时候)?(晚上|明天|后天|大后天|\d+天后|\d+小时后|明天\d+:\d+|\d+:\d+)'
        match = re.search(pattern, message, re.IGNORECASE)
        
        if not match:
            await ctx.send("提醒格式不正确～请使用类似格式：\n名字提醒我晚上看天气预报\n/名字 提醒我3天后看比赛\n/名字 提醒我明天20:30看电视")
            return
        
        content = match.group(1).strip()
        time_str = match.group(2).strip()
        
        # 解析时间
        time_info = self._parse_reminder_time(time_str)
        if not time_info:
            await ctx.send(f"无法识别的时间格式：{time_str}，请使用：晚上/明天/后天/X天后/X小时后/具体时间(如20:30)")
            return
        
        # 计算延迟时间（秒）
        delay_seconds = max(0, time_info["timestamp"] - time.time())
        
        if delay_seconds > 7 * 24 * 3600:  # 超过7天
            await ctx.send("提醒时间不能超过7天哦～")
            return
        
        if delay_seconds < 60:  # 少于1分钟
            await ctx.send("提醒时间太近啦，请设置至少1分钟后的提醒～")
            return
        
        # 添加提醒任务
        try:
            if SCHEDULER:
                # 生成唯一ID
                reminder_id = f"reminder_{user_id}_{int(time.time())}"
                
                # 获取当前活跃人格
                current_persona = GLOBAL_CURRENT_PERSONALITY
                persona_name = current_persona["command"] if current_persona else "名字"
                
                # 保存到数据库
                reminder_db_id = None
                if DB_MANAGER.enable:
                    reminder_db_id = DB_MANAGER.add_reminder(
                        user_id, 
                        content, 
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_info["timestamp"])), 
                        persona_name
                    )
                
                # 使用闭包捕获当前上下文信息
                async def send_reminder():
                    try:
                        # 构建提醒消息
                        reminder_msg = f"⏰ 提醒时间到啦！\n{persona_name}提醒你：{content}\n设置时间：{time_info['display']}"
                        
                        # 发送提醒
                        await ctx.send(f"@{user_id} {reminder_msg}")
                        
                        # 记录日志
                        LOGGER.info(f"发送提醒给用户{user_id}: {content}")
                        
                        # 从数据库删除已完成的提醒
                        if DB_MANAGER.enable and reminder_db_id:
                            DB_MANAGER.update_reminder_status(reminder_db_id, "completed")
                            
                    except Exception as e:
                        LOGGER.error(f"发送提醒失败：{str(e)}")
                
                # 添加定时任务
                SCHEDULER.add_job(
                    send_reminder,
                    'date',
                    run_date=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_info["timestamp"])),
                    id=reminder_id,
                    replace_existing=True
                )
                
                # 保存到内存
                if user_id not in USER_REMINDERS:
                    USER_REMINDERS[user_id] = []
                
                USER_REMINDERS[user_id].append({
                    "id": reminder_id,
                    "content": content,
                    "trigger_time": time_info["timestamp"],
                    "display_time": time_info["display"],
                    "persona_name": persona_name,
                    "status": "pending"
                })
                
                await ctx.send(f"✅ 已设置提醒：{time_info['display']} 提醒你【{content}】")
                
            else:
                await ctx.send("提醒功能暂时不可用～")
                
        except Exception as e:
            LOGGER.error(f"添加提醒失败：{str(e)}")
            await ctx.send(f"添加提醒失败：{str(e)}")

    async def _send_reminder_notification(self, reminder_id: int, user_id: str, content: str, persona_name: str):
        """发送提醒通知"""
        try:
            # 这里需要实际的发送消息逻辑
            # 由于没有实际的ctx，我们只能记录日志
            LOGGER.info(f"提醒通知：用户{user_id}，内容：{content}，人格：{persona_name}")
            
            # 更新数据库状态
            if DB_MANAGER.enable:
                DB_MANAGER.update_reminder_status(reminder_id, "completed")
                
        except Exception as e:
            LOGGER.error(f"发送提醒通知失败：{str(e)}")

    def _clean_expired_reminders(self):
        """清理过期的提醒"""
        try:
            if DB_MANAGER.enable:
                deleted_count = DB_MANAGER.delete_expired_reminders()
                if deleted_count > 0:
                    LOGGER.info(f"清理了{deleted_count}个过期提醒")
        except Exception as e:
            LOGGER.error(f"清理提醒失败：{str(e)}")

    async def _list_reminders(self, user_id: str, ctx: MessageContext):
        """列出用户的提醒"""
        try:
            reminders = []
            if DB_MANAGER.enable:
                reminders = DB_MANAGER.get_user_reminders(user_id, "pending")
            elif user_id in USER_REMINDERS:
                reminders = USER_REMINDERS[user_id]
            
            if not reminders:
                await ctx.send("你当前没有待处理的提醒哦～")
                return
            
            reminder_text = "📋 你的提醒列表：\n"
            for i, reminder in enumerate(reminders, 1):
                reminder_text += f"{i}. {reminder['content']}（{reminder.get('trigger_time', reminder.get('display_time', '未知时间'))}）\n"
            
            await ctx.send(reminder_text.strip())
            
        except Exception as e:
            LOGGER.error(f"列出提醒失败：{str(e)}")
            await ctx.send("列出提醒失败啦～")

    # ==================== 智能化进阶：意图+情绪+自主学习 ====================
    def _init_intelligence(self):
        """初始化意图识别、情绪强度识别、用户习惯学习"""
        # 意图识别规则（可扩展为本地BERT模型）
        self.intent_rules = {
            "comfort": ["好累", "难过", "崩溃", "不开心", "伤心"],
            "question": ["什么", "怎么", "如何", "为什么", "请教"],
            "share": ["分享", "今天", "我", "遇到", "发现"],
            "complain": ["吐槽", "烦", "讨厌", "垃圾", "生气"],
            "praise": ["好棒", "厉害", "优秀", "好看", "好听"]
        }

    def _recognize_user_intent(self, message: str) -> str:
        """识别用户意图"""
        for intent, keywords in self.intent_rules.items():
            if any(keyword in message for keyword in keywords):
                return intent
        return "general"  # 通用意图

    def _recognize_emotion_intensity(self, message: str) -> Tuple[str, str]:
        """识别用户情绪类型和强度（弱/中/强）"""
        emotion_keywords = {
            "happy": {
                "weak": ["开心", "高兴", "不错", "挺好"],
                "medium": ["超开心", "超棒", "太好", "惊喜"],
                "strong": ["狂喜", "激动", "疯了", "幸福"]
            },
            "sad": {
                "weak": ["难过", "失落", "不开心", "遗憾"],
                "medium": ["很伤心", "崩溃", "想哭", "委屈"],
                "strong": ["绝望", "心碎", "生无可恋", "痛苦"]
            },
            "angry": {
                "weak": ["生气", "烦躁", "讨厌", "不满"],
                "medium": ["很生气", "愤怒", "不爽", "恼火"],
                "strong": ["暴怒", "气炸", "恨", "抓狂"]
            },
            "neutral": {
                "weak": ["普通", "一般", "随便", "都行"],
                "medium": ["平静", "淡然", "无所谓", "还好"],
                "strong": ["冷漠", "无感", "麻木"]
            }
        }
        # 关键词匹配情绪
        for emotion, intensity_keywords in emotion_keywords.items():
            for intensity, keywords in intensity_keywords.items():
                if any(keyword in message for keyword in keywords):
                    return emotion, intensity
        # 用TextBlob增强情绪识别（如果已安装）
        if EMOTION_MODEL:
            polarity = EMOTION_MODEL(message).sentiment.polarity
            if polarity > 0.5:
                return "happy", "strong"
            elif polarity > 0:
                return "happy", "medium"
            elif polarity < -0.5:
                return "sad", "strong"
            elif polarity < 0:
                return "sad", "medium"
        return "neutral", "weak"  # 中性情绪

    def _update_user_habits(self, user_id: str, message: str):
        """更新用户聊天习惯（高频词、回复长度等）"""
        if not CONFIG["advanced"]["intelligence"]["persona_learning"]:
            return
        if user_id not in USER_HABITS:
            USER_HABITS[user_id] = {
                "high_freq_words": [],  # 高频词
                "reply_length": [],     # 回复长度
                "topic_preference": []  # 偏好话题
            }
        # 提取高频词（简单分词，可替换为jieba）
        words = message.strip().split()
        for word in words:
            if len(word) > 1 and word not in ["的", "了", "是", "我", "你", "他", "她", "它", "在", "和"]:
                USER_HABITS[user_id]["high_freq_words"].append(word)
        # 记录回复长度
        USER_HABITS[user_id]["reply_length"].append(len(message))
        # 提取偏好话题（基于意图）
        intent = self._recognize_user_intent(message)
        USER_HABITS[user_id]["topic_preference"].append(intent)
        # 每N轮对话修剪一次习惯数据
        if len(USER_HABITS[user_id]["reply_length"]) % CONFIG["advanced"]["intelligence"]["learning_cycle"] == 0:
            self._prune_user_habits(user_id)

    def _prune_user_habits(self, user_id: str):
        """修剪用户习惯数据，保留核心信息"""
        max_count = CONFIG["advanced"]["intelligence"]["max_habit_count"]
        # 高频词去重并按频率排序
        word_count = {}
        for word in USER_HABITS[user_id]["high_freq_words"]:
            word_count[word] = word_count.get(word, 0) + 1
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        USER_HABITS[user_id]["high_freq_words"] = [word for word, _ in sorted_words[:max_count]]
        # 回复长度取平均值
        if USER_HABITS[user_id]["reply_length"]:
            avg_length = int(sum(USER_HABITS[user_id]["reply_length"]) / len(USER_HABITS[user_id]["reply_length"]))
            USER_HABITS[user_id]["reply_length"] = [avg_length]
        # 偏好话题去重
        topic_count = {}
        for topic in USER_HABITS[user_id]["topic_preference"]:
            topic_count[topic] = topic_count.get(topic, 0) + 1
        sorted_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)
        USER_HABITS[user_id]["topic_preference"] = [topic for topic, _ in sorted_topics[:5]]

    # ==================== 智能缓存+LLM节流 ====================
    def _init_cache(self):
        """初始化缓存（Redis/本地）"""
        global CACHE_CLIENT
        cache_config = CONFIG["cache"]
        if not cache_config["enable"]:
            CACHE_CLIENT = None
            return
        if cache_config["cache_type"] == "redis":
            try:
                import redis
                CACHE_CLIENT = redis.Redis(
                    host=cache_config["redis_config"]["host"],
                    port=cache_config["redis_config"]["port"],
                    password=cache_config["redis_config"]["password"],
                    decode_responses=True
                )
                CACHE_CLIENT.ping()  # 测试连接
            except ImportError:
                LOGGER.warning("未安装redis，缓存降级为本地存储")
                CACHE_CLIENT = {}
            except Exception as e:
                LOGGER.error(f"Redis连接失败，缓存降级为本地存储：{str(e)}")
                CACHE_CLIENT = {}
        else:
            CACHE_CLIENT = {}  # 本地字典缓存

    def _get_cache_key(self, user_id: str, message: str, persona_name: str) -> str:
        """生成缓存Key（用户ID+消息+人格名）"""
        return hashlib.md5(f"{user_id}_{message}_{persona_name}".encode()).hexdigest()

    def _check_cache(self, user_id: str, message: str, persona_name: str) -> Optional[str]:
        """检查缓存，返回缓存回复（无则返回None）"""
        if not CONFIG["cache"]["enable"]:
            return None
        cache_key = self._get_cache_key(user_id, message, persona_name)
        if isinstance(CACHE_CLIENT, dict):
            if cache_key in CACHE_CLIENT and time.time() - CACHE_CLIENT[cache_key]["time"] < CONFIG["cache"]["cache_expire"]:
                # 节流检查：同一问题3分钟内不重复调用
                if CONFIG["cache"]["throttle"]:
                    throttle_key = f"throttle_{cache_key}"
                    if throttle_key in CACHE_CLIENT and time.time() - CACHE_CLIENT[throttle_key] < 180:
                        return CACHE_CLIENT[cache_key]["reply"]
                    CACHE_CLIENT[throttle_key] = time.time()
                return CACHE_CLIENT[cache_key]["reply"]
            return None
        else:
            try:
                cache_data = CACHE_CLIENT.get(cache_key)
                if not cache_data:
                    return None
                cache_data = json.loads(cache_data)
                if time.time() - cache_data["time"] < CONFIG["cache"]["cache_expire"]:
                    if CONFIG["cache"]["throttle"]:
                        throttle_key = f"throttle_{cache_key}"
                        throttle_time = CACHE_CLIENT.get(throttle_key)
                        if throttle_time and time.time() - float(throttle_time) < 180:
                            return cache_data["reply"]
                        CACHE_CLIENT.set(throttle_key, str(time.time()), ex=180)
                    return cache_data["reply"]
                return None
            except Exception as e:
                LOGGER.error(f"缓存查询失败：{str(e)}")
                return None

    def _set_cache(self, user_id: str, message: str, persona_name: str, reply: str):
        """设置缓存"""
        if not CONFIG["cache"]["enable"]:
            return
        cache_key = self._get_cache_key(user_id, message, persona_name)
        cache_data = {"reply": reply, "time": time.time()}
        if isinstance(CACHE_CLIENT, dict):
            CACHE_CLIENT[cache_key] = cache_data
        else:
            try:
                CACHE_CLIENT.set(cache_key, json.dumps(cache_data), ex=CONFIG["cache"]["cache_expire"])
            except Exception as e:
                LOGGER.error(f"缓存设置失败：{str(e)}")

    # ==================== 第三方工具集成 ====================
    def _init_tools(self):
        """初始化第三方工具"""
        self.tools = {}
        tools_config = CONFIG["tools"]
        if not tools_config["enable"]:
            return
        # 日历工具
        if tools_config["calendar"]["enable"] and 'icalendar' in locals():
            self.tools["calendar"] = {
                "type": "ical",
                "url": tools_config["calendar"]["ical_url"],
                "client": icalendar.Calendar
            }
        # 待办工具（本地存储）
        if tools_config["todo"]["enable"]:
            self.tools["todo"] = {
                "type": "local",
                "data_path": "./todo_data.json"
            }
            # 初始化待办数据文件
            if not os.path.exists(self.tools["todo"]["data_path"]):
                with open(self.tools["todo"]["data_path"], "w", encoding="utf-8") as f:
                    json.dump({}, f)
        # 天气工具（高德地图API）
        if tools_config["weather"]["enable"] and 'requests' in locals():
            self.tools["weather"] = {
                "type": "amap",
                "key": tools_config["weather"]["amap_key"],
                "city": tools_config["weather"]["city"]
            }

    async def _handle_tool_trigger(self, user_id: str, message: str, ctx: MessageContext) -> Optional[str]:
        """处理工具触发（返回工具回复，无则返回None）"""
        if not CONFIG["tools"]["enable"] or not self.tools:
            return None
        # 天气查询触发
        if any(keyword in message for keyword in ["天气", "温度", "下雨", "晴天", "预报"]):
            return await self._get_weather()
        # 待办工具触发
        if "待办" in message or "提醒" in message:
            if "添加" in message:
                todo_content = message.split("添加")[-1].strip()
                return await self._add_todo(user_id, todo_content)
            elif "查询" in message:
                return await self._query_todo(user_id)
            elif "完成" in message:
                todo_index = message.split("完成")[-1].strip()
                return await self._complete_todo(user_id, todo_index)
        # 日历工具触发
        if "日历" in message or "会议" in message or "日程" in message:
            return await self._get_calendar_events()
        return None

    async def _get_weather(self) -> str:
        """获取天气信息"""
        if "weather" not in self.tools:
            return "天气工具未启用～"
        weather_config = self.tools["weather"]
        try:
            url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={weather_config['key']}&city={weather_config['city']}&extensions=base"
            response = requests.get(url, timeout=5)
            data = response.json()
            if data["status"] != "1":
                return "查询天气失败啦～ 稍后再试试吧～"
            weather = data["lives"][0]
            return f"🌤️ 当前{weather['city']}天气：{weather['weather']}，温度{weather['temperature']}℃，湿度{weather['humidity']}%，{weather['info']}～"
        except Exception as e:
            LOGGER.error(f"天气查询失败：{str(e)}")
            return "查询天气失败啦～ 稍后再试试吧～"

    async def _add_todo(self, user_id: str, content: str) -> str:
        """添加待办"""
        if "todo" not in self.tools:
            return "待办工具未启用～"
        todo_config = self.tools["todo"]
        try:
            with open(todo_config["data_path"], "r", encoding="utf-8") as f:
                todo_data = json.load(f)
            if user_id not in todo_data:
                todo_data[user_id] = []
            todo_data[user_id].append({
                "content": content,
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "status": "pending"
            })
            with open(todo_config["data_path"], "w", encoding="utf-8") as f:
                json.dump(todo_data, f, ensure_ascii=False, indent=2)
            return f"✅ 已添加待办：{content}，记得按时完成哦～"
        except Exception as e:
            LOGGER.error(f"添加待办失败：{str(e)}")
            return "添加待办失败啦～ 稍后再试试吧～"

    async def _query_todo(self, user_id: str) -> str:
        """查询待办"""
        if "todo" not in self.tools:
            return "待办工具未启用～"
        todo_config = self.tools["todo"]
        try:
            with open(todo_config["data_path"], "r", encoding="utf-8") as f:
                todo_data = json.load(f)
            user_todos = todo_data.get(user_id, [])
            if not user_todos:
                return "你当前没有待办哦～ 可以添加新的待办呀～"
            todo_text = "📝 你的待办清单：\n"
            for i, todo in enumerate(user_todos, 1):
                status = "未完成" if todo["status"] == "pending" else "已完成"
                todo_text += f"{i}. {todo['content']}（{todo['time']} - {status}）\n"
            return todo_text.strip()
        except Exception as e:
            LOGGER.error(f"查询待办失败：{str(e)}")
            return "查询待办失败啦～ 稍后再试试吧～"

    async def _complete_todo(self, user_id: str, index_str: str) -> str:
        """完成待办"""
        if "todo" not in self.tools:
            return "待办工具未启用～"
        try:
            index = int(index_str) - 1
        except:
            return "请输入正确的待办序号（如/完成1）～"
        todo_config = self.tools["todo"]
        try:
            with open(todo_config["data_path"], "r", encoding="utf-8") as f:
                todo_data = json.load(f)
            user_todos = todo_data.get(user_id, [])
            if index < 0 or index >= len(user_todos):
                return "待办序号不存在～"
            user_todos[index]["status"] = "completed"
            with open(todo_config["data_path"], "w", encoding="utf-8") as f:
                json.dump(todo_data, f, ensure_ascii=False, indent=2)
            return f"✅ 已标记待办「{user_todos[index]['content']}」为已完成～"
        except Exception as e:
            LOGGER.error(f"完成待办失败：{str(e)}")
            return "完成待办失败啦～ 稍后再试试吧～"

    # ==================== 多模态交互（图片+语音） ====================
    def _init_multimodal(self):
        """初始化多模态交互"""
        self.multimodal = {}
        multimodal_config = CONFIG["multimodal"]
        if not multimodal_config["enable"]:
            return
        # 图片生成
        if multimodal_config["image_generate"]["enable"] and 'requests' in locals():
            self.multimodal["image"] = multimodal_config["image_generate"]
        # TTS语音合成（本地使用pyttsx3，云端可集成阿里云TTS）
        if multimodal_config["tts"]["enable"] and 'pyttsx3' in locals():
            tts_engine = pyttsx3.init()
            # 配置音色（根据人格映射）
            self.multimodal["tts"] = {
                "engine": tts_engine,
                "voice_map": multimodal_config["tts"]["voice_map"]
            }

    async def _generate_image(self, prompt: str, persona_name: str) -> Optional[str]:
        """生成图片（返回图片URL/Base64）"""
        if "image" not in self.multimodal:
            return None
        image_config = self.multimodal["image"]
        try:
            payload = {
                "prompt": prompt,
                "model": image_config["default_model"],
                "width": 512,
                "height": 512,
                "steps": 20
            }
            response = requests.post(image_config["sd_api_url"], json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                image_base64 = data["images"][0]
                return f"data:image/png;base64,{image_base64}"
            else:
                LOGGER.error(f"图片生成失败：{response.status_code} {response.text}")
                return None
        except Exception as e:
            LOGGER.error(f"图片生成失败：{str(e)}")
            return None

    async def _generate_voice(self, text: str, persona_name: str) -> Optional[str]:
        """生成语音（返回语音文件路径）"""
        if "tts" not in self.multimodal:
            return None
        tts_config = self.multimodal["tts"]
        voice = tts_config["voice_map"].get(persona_name, "female-neutral")
        try:
            # 生成临时语音文件
            voice_path = f"./temp_voice_{persona_name}_{int(time.time())}.mp3"
            engine = tts_config["engine"]
            # 调整音色和语速
            if voice == "female-cute":
                engine.setProperty("rate", 150)  # 语速
                engine.setProperty("volume", 1.0)  # 音量
            elif voice == "female-soft":
                engine.setProperty("rate", 130)
                engine.setProperty("volume", 0.9)
            engine.save_to_file(text, voice_path)
            engine.runAndWait()
            return voice_path
        except Exception as e:
            LOGGER.error(f"语音生成失败：{str(e)}")
            return None

    # ==================== 离线模式 ====================
    def _init_offline_mode(self):
        """初始化离线模式"""
        self.offline = {}
        offline_config = CONFIG["offline"]
        if not offline_config["enable"]:
            return
        # 加载离线回复模板
        if os.path.exists(offline_config["offline_templates"]):
            with open(offline_config["offline_templates"], "r", encoding="utf-8") as f:
                self.offline["templates"] = json.load(f)
        else:
            # 默认模板（适配8个人格）
            self.offline["templates"] = {
                "greeting": ["你好呀～ 我在离线模式等你哦～", "很高兴见到你～ 虽然没网，但我依然在～"],
                "switch_persona": ["已切换到{persona}～ 离线模式下也能聊天呀～"],
                "general": ["谢谢你的消息～ 我已经收到啦～", "哇～ 很有趣的分享呢～", "一起加油呀～"],
                "comfort": ["别难过啦～ 一切都会好起来的～", "我在这里陪着你呀～"],
                "food": ["听起来好好吃呀～ 离线模式也挡不住对美食的向往～"],
                "music": ["歌声是治愈的力量～ 离线也能感受到呀～"]
            }
        # 检查本地模型（仅记录路径，使用时加载）
        if os.path.exists(offline_config["local_model_path"]):
            self.offline["local_model"] = offline_config["local_model_path"]
        else:
            LOGGER.warning("本地模型路径不存在，离线模式仅支持模板回复")

    def _is_offline(self) -> bool:
        """检测是否离线（简单网络检测）"""
        if not CONFIG["offline"]["enable"]:
            return False
        try:
            if 'requests' not in locals():
                return True
            requests.get("https://www.baidu.com", timeout=3)
            return False
        except:
            return True

    def _get_offline_reply(self, message: str, persona_name: str) -> str:
        """获取离线回复（模板/本地模型）"""
        offline_config = self.offline
        # 匹配模板
        if any(keyword in message for keyword in ["你好", "哈喽", "hi"]):
            reply = random.choice(offline_config["templates"]["greeting"])
        elif any(p in message for p in PERSONALITIES.keys()):
            reply = random.choice(offline_config["templates"]["switch_persona"]).format(persona=persona_name)
        elif any(keyword in message for keyword in ["难过", "伤心", "不开心"]):
            reply = random.choice(offline_config["templates"]["comfort"])
        elif any(keyword in message for keyword in ["吃", "美食", "小笼包", "糖葫芦"]):
            reply = random.choice(offline_config["templates"]["food"])
        elif any(keyword in message for keyword in ["唱歌", "音乐", "歌声"]):
            reply = random.choice(offline_config["templates"]["music"])
        else:
            reply = random.choice(offline_config["templates"]["general"])
        # 本地模型（进阶，需加载llama.cpp等框架）
        if "local_model" in offline_config:
            try:
                # 示例：使用llama.cpp调用本地模型（需额外安装依赖）
                from llama_cpp import Llama
                llm = Llama(model_path=offline_config["local_model"], n_ctx=2048)
                persona_desc = PERSONALITIES[persona_name]["personality_desc"]
                output = llm(
                    f"人格：{persona_desc}，用户消息：{message}，回复：",
                    max_tokens=50,
                    temperature=0.7
                )
                reply = output["choices"][0]["text"].strip()
            except Exception as e:
                LOGGER.error(f"本地模型调用失败：{str(e)}")
        return f"【离线模式】{reply}"

    # ==================== 人格动态关系+成长系统 ====================
    def _init_persona_growth(self):
        """初始化人格成长系统"""
        self.growth = {}
        growth_config = CONFIG["persona_growth"]
        if not growth_config["enable"]:
            return
        # 初始化关系数据：{persona1: {persona2: {level: 1, interact_count: 0}}}
        self.growth["relationships"] = {}
        for p1 in PERSONALITIES.keys():
            self.growth["relationships"][p1] = {}
            for p2 in PERSONALITIES.keys():
                if p1 != p2:
                    self.growth["relationships"][p1][p2] = {"level": 1, "interact_count": 0}
        # 初始化成长数据：{persona: {interact_count: 0, unlocked: []}}
        self.growth["persona_data"] = {p: {"interact_count": 0, "unlocked": []} for p in PERSONALITIES.keys()}
        # 从数据库加载成长数据
        if DB_MANAGER.enable:
            cursor = DB_MANAGER.conn.cursor()
            # 加载关系数据
            cursor.execute("SELECT persona1, persona2, level, interact_count FROM persona_relationships")
            for p1, p2, level, count in cursor.fetchall():
                if p1 in self.growth["relationships"] and p2 in self.growth["relationships"][p1]:
                    self.growth["relationships"][p1][p2] = {"level": level, "interact_count": count}
            # 加载成长数据
            cursor.execute("SELECT persona_name, interact_count, unlocked FROM persona_growth")
            for p, count, unlocked in cursor.fetchall():
                if p in self.growth["persona_data"]:
                    self.growth["persona_data"][p]["interact_count"] = count
                    self.growth["persona_data"][p]["unlocked"] = json.loads(unlocked) if unlocked else []

    def _update_persona_relationship(self, persona1: str, persona2: str):
        """更新人格之间的关系（互动次数+升级）"""
        if not CONFIG["persona_growth"]["enable"]:
            return
        if persona1 not in self.growth["relationships"] or persona2 not in self.growth["relationships"][persona1]:
            return
        relationship = self.growth["relationships"][persona1][persona2]
        relationship["interact_count"] += 1
        # 关系升级逻辑
        growth_config = CONFIG["persona_growth"]["relationship_upgrade"]
        base_count = growth_config["base_count"]
        level_count = growth_config["level_count"]
        max_level = growth_config["max_level"]
        current_level = relationship["level"]
        if current_level < max_level:
            required_count = base_count + (current_level - 1) * level_count
            if relationship["interact_count"] >= required_count:
                relationship["level"] = current_level + 1
                LOGGER.info(f"人格关系升级：{persona1}与{persona2}从{current_level}级升级为{current_level+1}级")
        # 保存到数据库
        if DB_MANAGER.enable:
            cursor = DB_MANAGER.conn.cursor()
            cursor.execute("""
            REPLACE INTO persona_relationships (persona1, persona2, level, interact_count)
            VALUES (?, ?, ?, ?)
            """, (persona1, persona2, relationship["level"], relationship["interact_count"]))
            DB_MANAGER.conn.commit()

    def _update_persona_growth(self, persona_name: str):
        """更新人格成长进度（解锁新能力）"""
        if not CONFIG["persona_growth"]["enable"]:
            return
        if persona_name not in self.growth["persona_data"]:
            return
        growth_data = self.growth["persona_data"][persona_name]
        growth_data["interact_count"] += 1
        # 解锁逻辑
        unlock_config = CONFIG["persona_growth"]["growth_unlock"]
        unlocked = growth_data["unlocked"]
        for count_str, unlock_info in unlock_config.items():
            count = int(count_str)
            if growth_data["interact_count"] >= count and unlock_info not in unlocked:
                unlocked.append(unlock_info)
                LOGGER.info(f"人格{persona_name}解锁新能力：{unlock_info['type']} - {unlock_info['value']}")
                # 应用解锁能力（如新增情绪、技能）
                self._apply_unlock(persona_name, unlock_info)
        # 保存到数据库
        if DB_MANAGER.enable:
            cursor = DB_MANAGER.conn.cursor()
            cursor.execute("""
            REPLACE INTO persona_growth (persona_name, interact_count, unlocked)
            VALUES (?, ?, ?)
            """, (persona_name, growth_data["interact_count"], json.dumps(unlocked, ensure_ascii=False)))
            DB_MANAGER.conn.commit()

    def _apply_unlock(self, persona_name: str, unlock_info: Dict[str, str]):
        """应用解锁的能力"""
        if persona_name not in PERSONALITIES:
            return
        persona = PERSONALITIES[persona_name]
        if unlock_info["type"] == "emotion":
            # 新增情绪
            if "mood_triggers" not in persona:
                persona["mood_triggers"] = {}
            persona["mood_triggers"][f"解锁情绪{unlock_info['value']}"] = unlock_info["value"]
            if "mood_reply_style" not in persona:
                persona["mood_reply_style"] = {}
            # 新增情绪回复风格（默认配置，贴合人设）
            mood_style_map = {
                "兴奋": "语气极度活泼，多带🎉🔥颜文字，句子简短有力",
                "慵懒": "语气缓慢，带拖延感，少用颜文字",
                "傲娇": "表面冷淡，内心关心，带～～语气词",
                "温柔": "语气温柔细腻，多带😘颜文字，用共情表达",
                "坚定": "语气坚定有力，强调信念，少用修饰"
            }
            persona["mood_reply_style"][unlock_info["value"]] = mood_style_map.get(unlock_info["value"], "默认风格")
        elif unlock_info["type"] == "skill":
            # 新增技能（备用技能启用）
            if "skills" not in persona:
                persona["skills"] = {}
            persona["skills"][unlock_info["value"]] = {
                "command": f"/{unlock_info['value']}",
                "description": f"解锁的专属技能：{unlock_info['value']}",
                "prompt": f"以{persona_name}的人设，使用{unlock_info['value']}技能回复，贴合人格核心特质，不超过2句话"
            }
        elif unlock_info["type"] == "reply_style":
            # 新增回复风格
            if "advanced_reply_style" not in persona:
                persona["advanced_reply_style"] = {}
            persona["advanced_reply_style"][unlock_info["value"]] = {
                "description": f"高级回复风格：{unlock_info['value']}",
                "prompt": f"以{unlock_info['value']}风格回复，融合{persona_name}的核心人设（{persona['personality_desc']}）"
            }

    # ==================== 细粒度权限管理 ====================
    def _init_permission(self):
        """初始化权限管理"""
        self.permission = {}
        permission_config = CONFIG["permission"]
        if not permission_config["enable"]:
            return
        self.permission["roles"] = permission_config["roles"]
        self.permission["user_role_map"] = permission_config["user_role_map"]

    def _check_permission(self, user_id: str, operation: str) -> Tuple[bool, str]:
        """检查用户权限（返回是否允许+提示信息）"""
        if not CONFIG["permission"]["enable"]:
            return True, ""
        # 获取用户角色
        role = self.permission["user_role_map"].get(user_id, self.permission["user_role_map"]["default"])
        # 检查权限
        allowed_operations = self.permission["roles"][role]
        if "all" in allowed_operations or operation in allowed_operations:
            return True, ""
        else:
            return False, f"你没有{operation}权限（当前角色：{role}），请联系管理员升级权限～"

    def _log_operation(self, user_id: str, operation: str, result: str):
        """记录操作日志"""
        if not CONFIG["permission"]["enable"]:
            return
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if DB_MANAGER.enable:
            cursor = DB_MANAGER.conn.cursor()
            cursor.execute("""
            INSERT INTO operation_log (user_id, operation, time, result)
            VALUES (?, ?, ?, ?)
            """, (user_id, operation, time_str, result))
            DB_MANAGER.conn.commit()
        LOGGER.info(f"操作日志：用户{user_id} - {operation} - {result}")

    # ==================== 多场景深度适配 ====================
    def _init_scenes(self):
        """初始化场景（从配置+数据库加载）"""
        self.scenes = CONFIG["scene"]["default_scenes"].copy()
        # 用户当前场景：{user_id: 场景名}
        self.user_current_scene = {}
        # 场景默认人格：{场景名: 人格名}
        self.scene_default_persona = {CONFIG["scene"]["default_scene"]: DEFAULT_PERSONALITY["command"]}
        # 场景记忆隔离：{场景名: {user_id: {conversation: [], preference: {}}}}
        self.scene_memory = {}
        # 从数据库加载用户场景配置
        if DB_MANAGER.enable:
            cursor = DB_MANAGER.conn.cursor()
            # 加载用户当前场景
            cursor.execute("SELECT user_id, scene_name FROM user_current_scene")
            for user_id, scene_name in cursor.fetchall():
                if scene_name in self.scenes:
                    self.user_current_scene[user_id] = scene_name
            # 加载场景默认人格
            cursor.execute("SELECT scene_name, persona_name FROM scene_default_persona")
            for scene_name, persona_name in cursor.fetchall():
                if scene_name in self.scenes and persona_name in PERSONALITIES:
                    self.scene_default_persona[scene_name] = persona_name
            # 加载场景记忆
            cursor.execute("SELECT scene_name, user_id, conversation_json, preference_json FROM scene_memory")
            for scene_name, user_id, conv_json, pref_json in cursor.fetchall():
                if scene_name not in self.scene_memory:
                    self.scene_memory[scene_name] = {}
                self.scene_memory[scene_name][user_id] = {
                    "conversation": json.loads(conv_json) if conv_json else [],
                    "preference": json.loads(pref_json) if pref_json else {}
                }

    def _get_user_current_scene(self, user_id: str) -> str:
        """获取用户当前场景（默认通用场景）"""
        return self.user_current_scene.get(user_id, CONFIG["scene"]["default_scene"])

    def _save_scene_memory(self, user_id: str, scene_name: str):
        """保存场景记忆（对话历史+偏好）"""
        if not CONFIG["scene"]["scene_memory_isolation"]:
            return
        # 保存当前对话历史和偏好到场景记忆
        conversation = DB_MANAGER.get_conversation(user_id) if DB_MANAGER.enable else USER_CONVERSATION_HISTORY.get(user_id, [])
        preference = DB_MANAGER.get_preference(user_id) if DB_MANAGER.enable else USER_PREFERENCE.get(user_id, {})
        if scene_name not in self.scene_memory:
            self.scene_memory[scene_name] = {}
        self.scene_memory[scene_name][user_id] = {
            "conversation": conversation,
            "preference": preference
        }
        # 保存到数据库
        if DB_MANAGER.enable:
            cursor = DB_MANAGER.conn.cursor()
            conv_json = json.dumps(conversation, ensure_ascii=False)
            pref_json = json.dumps(preference, ensure_ascii=False)
            cursor.execute("""
            REPLACE INTO scene_memory (scene_name, user_id, conversation_json, preference_json)
            VALUES (?, ?, ?, ?)
            """, (scene_name, user_id, conv_json, pref_json))
            DB_MANAGER.conn.commit()

    def _load_scene_memory(self, user_id: str, scene_name: str):
        """加载场景记忆（对话历史+偏好）"""
        if not CONFIG["scene"]["scene_memory_isolation"]:
            return
        # 从场景记忆加载对话历史和偏好
        if scene_name in self.scene_memory and user_id in self.scene_memory[scene_name]:
            memory = self.scene_memory[scene_name][user_id]
            # 加载对话历史
            if not DB_MANAGER.enable:
                USER_CONVERSATION_HISTORY[user_id] = memory["conversation"]
            # 加载偏好
            if DB_MANAGER.enable:
                DB_MANAGER.update_preference(user_id, memory["preference"])
            else:
                USER_PREFERENCE[user_id] = memory["preference"]
        else:
            # 场景无记忆，初始化空记忆
            if DB_MANAGER.enable:
                cursor = DB_MANAGER.conn.cursor()
                cursor.execute("""
                INSERT INTO scene_memory (scene_name, user_id, conversation_json, preference_json)
                VALUES (?, ?, ?, ?)
                """, (scene_name, user_id, json.dumps([]), json.dumps({})))
                DB_MANAGER.conn.commit()
            else:
                if scene_name not in self.scene_memory:
                    self.scene_memory[scene_name] = {}
                self.scene_memory[scene_name][user_id] = {"conversation": [], "preference": {}}

    def _get_scene_specific_config(self, persona: Dict[str, Any], scene_name: str) -> Dict[str, Any]:
        """获取人格的场景专属配置（无则返回全局配置）"""
        if not CONFIG["scene"]["scene_specific_config"]:
            return {
                "reply_style": persona["reply_style"],
                "plan_style": persona.get("plan_style", ""),
                "private_plan_style": persona.get("private_plan_style", ""),
                "speak_frequency": "medium",
                "visual_style": persona.get("visual_style", "")
            }
        # 场景专属配置（覆盖全局）
        scene_config = persona.get("scene_config", {}).get(scene_name, {})
        return {
            "reply_style": scene_config.get("reply_style", persona["reply_style"]),
            "plan_style": scene_config.get("plan_style", persona.get("plan_style", "")),
            "private_plan_style": scene_config.get("private_plan_style", persona.get("private_plan_style", "")),
            "speak_frequency": scene_config.get("speak_frequency", "medium"),
            "visual_style": scene_config.get("visual_style", persona.get("visual_style", ""))
        }
    
    # ==================== 人格热插拔功能 ====================
    async def _import_persona(self, user_id: str, filename: str, ctx: MessageContext):
        """指令导入人格：/import_persona 文件名（需放在external_persona_dir目录）"""
        external_dir = CONFIG["hot_swap"]["external_persona_dir"]
        filepath = os.path.join(external_dir, filename)
        if not os.path.exists(filepath):
            await ctx.send(f"未找到文件：{filename}（请放入{external_dir}目录）")
            return
        ext = filename.split(".")[-1]
        if ext not in CONFIG["hot_swap"]["support_formats"]:
            await ctx.send(f"不支持的格式：{ext}，仅支持{CONFIG['hot_swap']['support_formats']}")
            return
        # 加载并验证人格
        try:
            if ext == "toml":
                with open(filepath, "r", encoding="utf-8") as f:
                    persona_data = toml.load(f)
            elif ext == "json":
                with open(filepath, "r", encoding="utf-8") as f:
                    persona_data = json.load(f)
            required_fields = ["command", "trigger_names", "personality_desc", "reply_style"]
            if not all(field in persona_data for field in required_fields):
                await ctx.send("人格文件缺少必填字段（command/trigger_names/personality_desc/reply_style）")
                return
            persona_name = persona_data["command"]
            if persona_name in PERSONALITIES:
                await ctx.send(f"人格「{persona_name}」已存在，是否覆盖？发送Y确认/N取消")
                # 等待用户确认
                def check_confirm(msg):
                    return msg.user.id == user_id and msg.content.strip().upper() in ["Y", "N"]
                try:
                    confirm_msg = await self.bot.wait_for_message(check_confirm, timeout=30)
                    if confirm_msg.content.strip().upper() != "Y":
                        await ctx.send("已取消覆盖")
                        return
                except asyncio.TimeoutError:
                    await ctx.send("确认超时，已取消")
                    return
            # 补全默认字段（确保兼容性）
            default_fields = {
                "default_mood": "平静",
                "mood_triggers": {},
                "mood_reply_style": {},
                "scene_whitelist": ["general"],
                "scene_config": {},
                "interaction_relations": {},
                "watermark": f"[{persona_name}]",
                "preference_tag": "自定义",
                "reply_when_called": f"{persona_name}在呢～",
                "reply_when_random": f"{persona_name}突然出现啦～"
            }
            for field, value in default_fields.items():
                if field not in persona_data:
                    persona_data[field] = value
            # 导入人格
            PERSONALITIES[persona_name] = persona_data
            CUSTOM_PERSONALITIES[persona_name] = {**persona_data, "creator": user_id, "source": "imported"}
            PERSONA_MOOD[persona_name] = persona_data.get("default_mood", "平静")
            if DB_MANAGER.enable:
                cursor = DB_MANAGER.conn.cursor()
                cursor.execute("REPLACE INTO persona_stats (persona_name, switch_count) VALUES (?, ?)", (persona_name, 0))
                DB_MANAGER.conn.commit()
            await ctx.send(f"✅ 成功导入人格「{persona_name}」，发送名字或/{persona_name}即可切换")
            LOGGER.info(f"用户{user_id}导入人格：{persona_name}（来自{filename}）")
        except Exception as e:
            await ctx.send(f"导入失败：{str(e)}")
            LOGGER.error(f"用户{user_id}导入人格失败：{str(e)}")

    async def _export_persona(self, user_id: str, persona_name: str, ctx: MessageContext):
        """指令导出人格：/export_persona 人格名（导出到external_persona_dir目录）"""
        if persona_name not in PERSONALITIES:
            await ctx.send(f"人格「{persona_name}」不存在")
            return
        # 检查权限（仅创建者或管理员可导出）
        if persona_name in CUSTOM_PERSONALITIES:
            creator = CUSTOM_PERSONALITIES[persona_name].get("creator")
            if creator != user_id and user_id != "admin":
                await ctx.send("你无权导出该人格（仅创建者或管理员可导出）")
                return
        # 导出为TOML文件（默认格式）
        external_dir = CONFIG["hot_swap"]["external_persona_dir"]
        os.makedirs(external_dir, exist_ok=True)
        export_filename = f"{persona_name}_export_{int(time.time())}.toml"
        export_path = os.path.join(external_dir, export_filename)
        # 过滤敏感字段（如API密钥）
        export_data = PERSONALITIES[persona_name].copy()
        sensitive_fields = ["api_key", "secret", "token"]
        for field in sensitive_fields:
            if field in export_data:
                export_data[field] = "***"
        # 写入文件
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                toml.dump(export_data, f)
            await ctx.send(f"✅ 成功导出人格「{persona_name}」到：{export_path}")
            LOGGER.info(f"用户{user_id}导出人格：{persona_name}（保存到{export_path}）")
        except Exception as e:
            await ctx.send(f"导出失败：{str(e)}")
            LOGGER.error(f"用户{user_id}导出人格失败：{str(e)}")

    async def _delete_persona(self, user_id: str, persona_name: str, ctx: MessageContext):
        """指令删除自定义人格：/delete_persona 人格名（仅删除自定义导入的人格）"""
        # 保护内置人格
        builtin_personas = ["名字", "滴滴喵", "陆尔泠", "元气少女", "高冷御姐", "温柔学长", "沙雕网友", "文艺青年"]
        if persona_name in builtin_personas:
            await ctx.send("内置人格不允许删除～")
            return
        if persona_name not in PERSONALITIES or persona_name not in CUSTOM_PERSONALITIES:
            await ctx.send(f"自定义人格「{persona_name}」不存在～")
            return
        # 检查权限
        creator = CUSTOM_PERSONALITIES[persona_name].get("creator")
        if creator != user_id and user_id != "admin":
            await ctx.send("你无权删除该人格（仅创建者或管理员可删除）")
            return
        # 确认删除
        await ctx.send(f"确定要删除人格「{persona_name}」吗？发送Y确认/N取消")
        def check_confirm(msg):
            return msg.user.id == user_id and msg.content.strip().upper() in ["Y", "N"]
        try:
            confirm_msg = await self.bot.wait_for_message(check_confirm, timeout=30)
            if confirm_msg.content.strip().upper() != "Y":
                await ctx.send("已取消删除～")
                return
        except asyncio.TimeoutError:
            await ctx.send("确认超时，已取消删除～")
            return
        # 执行删除
        try:
            del PERSONALITIES[persona_name]
            del CUSTOM_PERSONALITIES[persona_name]
            if persona_name in PERSONA_MOOD:
                del PERSONA_MOOD[persona_name]
            # 清理数据库
            if DB_MANAGER.enable:
                cursor = DB_MANAGER.conn.cursor()
                cursor.execute("DELETE FROM persona_stats WHERE persona_name = ?", (persona_name,))
                cursor.execute("DELETE FROM persona_relationships WHERE persona1 = ? OR persona2 = ?", (persona_name, persona_name))
                cursor.execute("DELETE FROM persona_growth WHERE persona_name = ?", (persona_name,))
                DB_MANAGER.conn.commit()
            await ctx.send(f"✅ 成功删除自定义人格「{persona_name}」～")
            LOGGER.info(f"用户{user_id}删除自定义人格：{persona_name}")
        except Exception as e:
            await ctx.send(f"删除失败：{str(e)}")
            LOGGER.error(f"用户{user_id}删除人格失败：{str(e)}")

    # ==================== 监控面板+可视化配置 ====================
    def _init_monitor_app(self):
        """初始化监控面板（独立线程启动Flask）"""
        if not CONFIG["monitor"]["enable"]:
            return
        self.monitor_app = create_monitor_app()
        # 独立线程启动Flask服务
        def run_monitor():
            self.monitor_app.run(
                host=CONFIG["monitor"]["host"],
                port=CONFIG["monitor"]["port"],
                debug=False,
                use_reloader=False
            )
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        LOGGER.info(f"监控面板已启动：http://{CONFIG['monitor']['host']}:{CONFIG['monitor']['port']}")

    def _init_web_config(self):
        """初始化可视化配置工具（Web端修改config.toml）"""
        if not CONFIG["web_config"]["enable"]:
            return
        # 简化版Web配置工具（独立应用）
        if not HAS_FLASK:
            LOGGER.warning("Flask未安装，可视化配置工具禁用")
            return
        
        web_app = Flask(__name__)
        web_app.secret_key = "persona_web_config_secret"
        
        # 简单的登录检查函数
        def check_login():
            if not session.get("logged_in"):
                return False
            return True
        
        # 登录页面
        @web_app.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "POST":
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "").strip()
                # 使用监控面板的用户名密码
                if (username == CONFIG["monitor"]["username"] and 
                    password == CONFIG["monitor"]["password"]):
                    session["logged_in"] = True
                    return redirect(url_for("config_home"))
                return "用户名或密码错误"
            
            return '''
            <h2>可视化配置工具登录</h2>
            <form method="post">
                用户名：<input type="text" name="username"><br>
                密码：<input type="password" name="password"><br>
                <input type="submit" value="登录">
            </form>
            '''
        
        # 配置主页 - 需要登录
        @web_app.route("/")
        def config_home():
            if not check_login():
                return redirect(url_for("login"))
            
            # 获取插件状态
            plugin_status = {
                "personality_count": len(PERSONALITIES),
                "active_persona": GLOBAL_CURRENT_PERSONALITY["command"] if GLOBAL_CURRENT_PERSONALITY else "None",
                "database_enabled": CONFIG["database"]["enable"],
                "cache_enabled": CONFIG["cache"]["enable"]
            }
            
            return f'''
            <h1>人格切换插件可视化配置工具 v9.0.1</h1>
            <h2>插件状态</h2>
            <ul>
                <li>人格数量：{plugin_status['personality_count']}</li>
                <li>当前活跃人格：{plugin_status['active_persona']}</li>
                <li>数据库状态：{'已启用' if plugin_status['database_enabled'] else '已禁用'}</li>
                <li>缓存状态：{'已启用' if plugin_status['cache_enabled'] else '已禁用'}</li>
            </ul>
            <h2>配置选项</h2>
            <ul>
                <li><a href="/personalities">人格配置</a></li>
                <li><a href="/system">系统配置</a></li>
                <li><a href="/logout">退出登录</a></li>
            </ul>
            '''
        
        # 人格配置页面
        @web_app.route("/personalities", methods=["GET", "POST"])
        def personalities_config():
            if not check_login():
                return redirect(url_for("login"))
            
            if request.method == "POST":
                # 保存配置
                try:
                    for persona_name in PERSONALITIES.keys():
                        reply_style = request.form.get(f"{persona_name}_reply_style", "").strip()
                        if reply_style:
                            PERSONALITIES[persona_name]["reply_style"] = reply_style
                    
                    # 保存到config.toml
                    with open(os.path.join(os.path.dirname(__file__), "config.toml"), "w", encoding="utf-8") as f:
                        toml.dump(CONFIG, f)
                    
                    return '''
                    <script>
                        alert("配置已保存！");
                        window.location.href = "/personalities";
                    </script>
                    '''
                except Exception as e:
                    return f"保存失败：{str(e)}<br><a href='/personalities'>返回</a>"
            
            # 显示当前配置
            form_html = '''
            <h2>人格配置</h2>
            <form method="post">
            '''
            for persona_name, persona_data in PERSONALITIES.items():
                reply_style = persona_data.get("reply_style", "")
                personality_desc = persona_data.get("personality_desc", "")
                form_html += f'''
                <div style="border:1px solid #ccc; padding:15px; margin-bottom:15px; border-radius:5px;">
                    <h3>{persona_name}</h3>
                    <div>
                        <strong>人格描述：</strong><br>
                        <textarea name="{persona_name}_personality_desc" rows="3" cols="80" readonly>{personality_desc}</textarea>
                    </div>
                    <div>
                        <strong>回复风格：</strong><br>
                        <textarea name="{persona_name}_reply_style" rows="4" cols="80">{reply_style}</textarea>
                    </div>
                </div>
                '''
            
            form_html += '''
            <input type="submit" value="保存配置">
            <a href="/" style="margin-left:20px;">返回主页</a>
            </form>
            '''
            
            return form_html
        
        # 系统配置页面
        @web_app.route("/system", methods=["GET", "POST"])
        def system_config():
            if not check_login():
                return redirect(url_for("login"))
            
            if request.method == "POST":
                try:
                    # 更新LLM配置
                    llm_config = CONFIG["llm"]
                    llm_config["temperature"] = float(request.form.get("temperature", 0.7))
                    llm_config["max_tokens"] = int(request.form.get("max_tokens", 300))
                    
                    # 更新缓存配置
                    cache_config = CONFIG["cache"]
                    cache_config["enable"] = request.form.get("cache_enable") == "on"
                    cache_config["cache_expire"] = int(request.form.get("cache_expire", 3600))
                    
                    # 保存到config.toml
                    with open(os.path.join(os.path.dirname(__file__), "config.toml"), "w", encoding="utf-8") as f:
                        toml.dump(CONFIG, f)
                    
                    return '''
                    <script>
                        alert("系统配置已保存！");
                        window.location.href = "/system";
                    </script>
                    '''
                except Exception as e:
                    return f"保存失败：{str(e)}<br><a href='/system'>返回</a>"
            
            # 显示当前系统配置
            llm_config = CONFIG["llm"]
            cache_config = CONFIG["cache"]
            
            return f'''
            <h2>系统配置</h2>
            <form method="post">
                <h3>LLM配置</h3>
                <div>
                    <label>温度（temperature）：</label>
                    <input type="number" name="temperature" step="0.1" min="0" max="2" value="{llm_config.get('temperature', 0.7)}">
                    <small>值越高回复越随机，值越低回复越确定</small>
                </div>
                <div>
                    <label>最大令牌数（max_tokens）：</label>
                    <input type="number" name="max_tokens" min="50" max="2000" value="{llm_config.get('max_tokens', 300)}">
                    <small>控制回复的最大长度</small>
                </div>
                
                <h3>缓存配置</h3>
                <div>
                    <label>
                        <input type="checkbox" name="cache_enable" {'checked' if cache_config.get('enable', True) else ''}>
                        启用缓存
                    </label>
                </div>
                <div>
                    <label>缓存过期时间（秒）：</label>
                    <input type="number" name="cache_expire" min="60" max="86400" value="{cache_config.get('cache_expire', 3600)}">
                </div>
                
                <br>
                <input type="submit" value="保存配置">
                <a href="/" style="margin-left:20px;">返回主页</a>
            </form>
            '''
        
        # 退出登录
        @web_app.route("/logout")
        def logout():
            session.pop("logged_in", None)
            return redirect(url_for("login"))
        
        # 独立线程启动Web配置工具
        def run_web_app():
            try:
                web_app.run(
                    host=CONFIG["web_config"]["host"],
                    port=CONFIG["web_config"]["port"],
                    debug=False,
                    use_reloader=False
                )
            except Exception as e:
                LOGGER.error(f"Web配置工具启动失败：{str(e)}")
        
        web_thread = threading.Thread(target=run_web_app, daemon=True)
        web_thread.start()
        LOGGER.info(f"可视化配置工具已启动：http://{CONFIG['web_config']['host']}:{CONFIG['web_config']['port']}")
    
    # ==================== 数据备份与迁移 ====================
    def _auto_backup(self):
        """自动备份数据（对话历史+人格配置+用户偏好）"""
        backup_config = CONFIG["backup"]
        backup_dir = backup_config["backup_dir"]
        os.makedirs(backup_dir, exist_ok=True)
        backup_filename = f"backup_{int(time.time())}.json"
        backup_path = os.path.join(backup_dir, backup_filename)
        # 备份核心数据
        backup_data = {
            "personalities": PERSONALITIES,
            "user_preference": USER_PREFERENCE,
            "user_conversation": USER_CONVERSATION_HISTORY,
            "persona_stats": GLOBAL_SHARED_MEMORY["personality_stats"],
            "scene_memory": self.scene_memory
        }
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            LOGGER.info(f"自动备份完成：{backup_path}")
            # 清理过期备份
            self._clean_old_backups(backup_dir, backup_config["backup_retention_days"])
        except Exception as e:
            LOGGER.error(f"自动备份失败：{str(e)}")

    def _clean_old_backups(self, backup_dir: str, retention_days: int):
        """清理过期备份"""
        now = time.time()
        retention_seconds = retention_days * 24 * 3600
        for filename in os.listdir(backup_dir):
            if filename.startswith("backup_") and filename.endswith(".json"):
                filepath = os.path.join(backup_dir, filename)
                file_mtime = os.path.getmtime(filepath)
                if now - file_mtime > retention_seconds:
                    os.remove(filepath)
                    LOGGER.info(f"清理过期备份：{filepath}")

    def _load_backup(self):
        """加载最新备份（启动时恢复数据）"""
        backup_config = CONFIG["backup"]
        if not backup_config["enable"] or not backup_config["auto_restore"]:
            return
        backup_dir = backup_config["backup_dir"]
        if not os.path.exists(backup_dir):
            return
        # 找到最新备份
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith("backup_") and f.endswith(".json")]
        if not backup_files:
            return
        latest_file = max(backup_files, key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)))
        latest_path = os.path.join(backup_dir, latest_file)
        # 加载备份数据
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            # 恢复数据
            global PERSONALITIES, USER_PREFERENCE, USER_CONVERSATION_HISTORY
            PERSONALITIES.update(backup_data.get("personalities", {}))
            USER_PREFERENCE.update(backup_data.get("user_preference", {}))
            USER_CONVERSATION_HISTORY.update(backup_data.get("user_conversation", {}))
            GLOBAL_SHARED_MEMORY["personality_stats"].update(backup_data.get("persona_stats", {}))
            self.scene_memory.update(backup_data.get("scene_memory", {}))
            LOGGER.info(f"从备份恢复数据：{latest_path}")
        except Exception as e:
            LOGGER.error(f"加载备份失败：{str(e)}")
    
    # ==================== 核心消息处理逻辑 ====================
    @on_message
    async def handle_message(self, ctx: MessageContext):
        """处理所有用户消息，核心入口"""
        # 提前声明要修改的全局变量（关键修复点）
        global GLOBAL_CURRENT_PERSONALITY, PERSONA_MOOD
        
        user_id = ctx.user.id
        message = ctx.content.strip()
        current_time = time.time()

        # 关键：添加详细日志
        LOGGER.info(f"=== 人格插件收到消息 ===")
        LOGGER.info(f"用户: {user_id}, 消息: {message}")
        LOGGER.info(f"当前活跃人格: {GLOBAL_CURRENT_PERSONALITY['command'] if GLOBAL_CURRENT_PERSONALITY else 'None'}")
        LOGGER.info(f"已加载人格数: {len(PERSONALITIES)}")
        LOGGER.info(f"人格列表: {list(PERSONALITIES.keys())}")

        # 1. 离线模式检测
        if self._is_offline():
            persona_name = GLOBAL_CURRENT_PERSONALITY["command"]
            offline_reply = self._get_offline_reply(message, persona_name)
            await ctx.send(offline_reply)
            return

        # 2. 权限检查（基础操作）
        permission_allowed, permission_msg = self._check_permission(user_id, "message.handle")
        if not permission_allowed:
            await ctx.send(permission_msg)
            self._log_operation(user_id, "message.handle", f"拒绝：无权限")
            return

        # 3. 工具触发检测
        tool_reply = await self._handle_tool_trigger(user_id, message, ctx)
        if tool_reply:
            await ctx.send(tool_reply)
            return

        # 3.5. 提醒功能检测
        if "提醒" in message and ("我" in message or "你" in message):
            await self._add_reminder(user_id, message, ctx)
            self._log_operation(user_id, "add_reminder", f"添加提醒：{message}")
            return

        # 3.6. 列出提醒
        if "我的提醒" in message or "列出提醒" in message or "查看提醒" in message:
            await self._list_reminders(user_id, ctx)
            return

        # 4. 人格热插拔指令处理
        if message.startswith("/import_persona"):
            filename = message.split(" ", 1)[1].strip() if len(message.split(" ", 1)) > 1 else ""
            await self._import_persona(user_id, filename, ctx)
            self._log_operation(user_id, "import_persona", f"导入人格：{filename}")
            return
        elif message.startswith("/export_persona"):
            persona_name = message.split(" ", 1)[1].strip() if len(message.split(" ", 1)) > 1 else ""
            await self._export_persona(user_id, persona_name, ctx)
            self._log_operation(user_id, "export_persona", f"导出人格：{persona_name}")
            return
        elif message.startswith("/delete_persona"):
            persona_name = message.split(" ", 1)[1].strip() if len(message.split(" ", 1)) > 1 else ""
            await self._delete_persona(user_id, persona_name, ctx)
            self._log_operation(user_id, "delete_persona", f"删除人格：{persona_name}")
            return

        # 5. 场景切换指令
        if message.startswith("/switch_scene"):
            scene_name = message.split(" ", 1)[1].strip() if len(message.split(" ", 1)) > 1 else ""
            if scene_name not in self.scenes:
                await ctx.send(f"场景「{scene_name}」不存在，支持的场景：{list(self.scenes.keys())}")
                return
            # 保存当前场景记忆
            current_scene = self._get_user_current_scene(user_id)
            self._save_scene_memory(user_id, current_scene)
            # 切换场景并加载新场景记忆
            self.user_current_scene[user_id] = scene_name
            self._load_scene_memory(user_id, scene_name)
            # 切换场景默认人格（已提前声明global，此处可直接修改）
            default_persona = self.scene_default_persona.get(scene_name, DEFAULT_PERSONALITY["command"])
            if default_persona in PERSONALITIES:
                GLOBAL_CURRENT_PERSONALITY = PERSONALITIES[default_persona]
                await ctx.send(f"✅ 切换到{scene_name}场景，已自动切换为场景默认人格：{default_persona}")
            else:
                await ctx.send(f"✅ 切换到{scene_name}场景（无默认人格）")
            # 保存到数据库
            if DB_MANAGER.enable:
                cursor = DB_MANAGER.conn.cursor()
                cursor.execute("REPLACE INTO user_current_scene (user_id, scene_name) VALUES (?, ?)", (user_id, scene_name))
                DB_MANAGER.conn.commit()
            self._log_operation(user_id, "switch_scene", f"切换到场景：{scene_name}")
            return

        # 6. 人格切换检测（指令/触发词）
        target_persona = None
        # 指令切换（如/名字）
        if message.startswith("/"):
            cmd = message[1:].strip()
            if cmd in PERSONALITIES:
                target_persona = PERSONALITIES[cmd]
        # 触发词切换
        else:
            for name, persona in PERSONALITIES.items():
                if any(trigger in message for trigger in persona["trigger_names"]):
                    target_persona = persona
                    break

        # 7. 执行人格切换
        if target_persona:
            old_persona = GLOBAL_CURRENT_PERSONALITY
            GLOBAL_CURRENT_PERSONALITY = target_persona
            
            LOGGER.info(f"=== 执行人格切换 ===")
            LOGGER.info(f"旧人格: {old_persona['command'] if old_persona else 'None'}")
            LOGGER.info(f"新人格: {target_persona['command']}")
            
            # 关键修复：切换全局人格配置
            LOGGER.info(f"开始切换全局人格配置...")
            switch_success = switch_global_personality(target_persona["command"])
            if switch_success:
                LOGGER.info(f"✅ 全局人格配置更新成功")
            else:
                LOGGER.error(f"❌ 全局人格配置更新失败")
            
            # 更新人格关系（旧→新）
            self._update_persona_relationship(old_persona["command"], target_persona["command"])
            # 更新人格成长
            self._update_persona_growth(target_persona["command"])
            # 记录切换日志
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            DB_MANAGER.insert_switch_record(user_id, time_str, target_persona["command"], "manual")
            # 更新用户偏好
            preference = DB_MANAGER.get_preference(user_id) if DB_MANAGER.enable else USER_PREFERENCE.get(user_id, {})
            preference[target_persona["command"]] = preference.get(target_persona["command"], 0) + 1
            if DB_MANAGER.enable:
                DB_MANAGER.update_preference(user_id, preference)
            else:
                USER_PREFERENCE[user_id] = preference
            # 发送切换回复
            switch_reply = target_persona.get("reply_when_called", f"{target_persona['command']}来啦～")
            await ctx.send(switch_reply)
            self._log_operation(user_id, "switch_persona", f"切换到：{target_persona['command']}")
            return

        # 8. 显示人格列表（修复版）
        if "人格列表" in message or "/人格列表" in message or "!人格列表" in message:
            LOGGER.info(f"用户请求人格列表，已加载{len(PERSONALITIES)}个人格")
            
            # 构建完整的人格列表
            persona_list = "🎭 **人格切换插件 v9.0.1 - 可用人格列表**\n\n"
            
            # 显示所有已加载人格
            for i, (name, persona) in enumerate(PERSONALITIES.items(), 1):
                description = persona.get("description", persona.get("personality_desc", "无描述"))
                trigger_names = ", ".join(persona.get("trigger_names", []))
                
                # 标记当前活跃人格
                is_active = GLOBAL_CURRENT_PERSONALITY and GLOBAL_CURRENT_PERSONALITY["command"] == name
                active_mark = "🌟 " if is_active else ""
                
                persona_list += f"{active_mark}{i}. **{name}**\n"
                persona_list += f"   描述: {description[:50]}...\n"
                persona_list += f"   触发词: {trigger_names}\n"
                persona_list += f"   指令: /{name}\n"
                
                # 显示默认情绪（如果有）
                default_mood = persona.get("default_mood", "")
                if default_mood:
                    persona_list += f"   默认情绪: {default_mood}\n"
                
                persona_list += "\n"
            
            # 添加统计信息
            persona_list += f"📊 **统计信息**\n"
            persona_list += f"• 总人格数: {len(PERSONALITIES)} 个\n"
            persona_list += f"• 当前活跃: {GLOBAL_CURRENT_PERSONALITY['command'] if GLOBAL_CURRENT_PERSONALITY else 'None'}\n"
            
            # 获取人格活跃度
            if DB_MANAGER.enable:
                stats = DB_MANAGER.get_persona_stats()
                if stats:
                    top_personas = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:3]
                    persona_list += f"• 最活跃人格: {', '.join([f'{p}({c})' for p, c in top_personas])}\n"
            
            # 添加使用提示
            persona_list += "\n💡 **使用提示**\n"
            persona_list += "• 发送人格名称或使用 /人格名 切换\n"
            persona_list += "• 使用 /人格列表 查看此列表\n"
            persona_list += "• 使用 /switch_scene 场景名 切换场景\n"
            
            # 确保消息不超过长度限制
            if len(persona_list) > 2000:
                # 分割消息
                parts = []
                lines = persona_list.split('\n')
                current_part = ""
                
                for line in lines:
                    if len(current_part) + len(line) + 1 < 2000:
                        current_part += line + '\n'
                    else:
                        parts.append(current_part)
                        current_part = line + '\n'
                
                if current_part:
                    parts.append(current_part)
                
                # 发送所有部分
                for i, part in enumerate(parts):
                    if i == 0:
                        await ctx.send(part.strip())
                    else:
                        await ctx.send(f"（续第{i+1}部分）\n{part.strip()}")
            else:
                await ctx.send(persona_list.strip())
            
            LOGGER.info(f"已发送完整人格列表，共{len(PERSONALITIES)}个人格")
            return

        # 9. 智能化交互（意图+情绪识别）
        user_intent = self._recognize_user_intent(message)
        user_emotion, emotion_intensity = self._recognize_emotion_intensity(message)
        # 更新用户习惯
        self._update_user_habits(user_id, message)

        # 10. 缓存检查
        current_persona_name = GLOBAL_CURRENT_PERSONALITY["command"]
        cache_reply = self._check_cache(user_id, message, current_persona_name)
        if cache_reply:
            await ctx.send(cache_reply)
            return

        # 11. 构建LLM提示词（融合人格+场景+情绪+意图）
        current_scene = self._get_user_current_scene(user_id)
        scene_config = self._get_scene_specific_config(GLOBAL_CURRENT_PERSONALITY, current_scene)
        # 人格核心描述
        persona_desc = GLOBAL_CURRENT_PERSONALITY["personality_desc"]
        # 情绪适配
        current_mood = PERSONA_MOOD[current_persona_name]
        mood_style = GLOBAL_CURRENT_PERSONALITY.get("mood_reply_style", {}).get(current_mood, scene_config["reply_style"])
        # 构建提示词
        prompt = f"""
        你现在的身份是：{persona_desc}
        当前场景：{current_scene}，场景专属回复风格：{scene_config['reply_style']}
        当前情绪：{current_mood}，情绪回复风格：{mood_style}
        用户意图：{user_intent}，用户情绪：{user_emotion}（强度：{emotion_intensity}）
        用户消息：{message}
        回复要求：
        1. 严格贴合人格设定和当前情绪，不偏离人设
        2. 适配当前场景，符合场景回复风格
        3. 回应用户的情绪和意图，有共情力
        4. 回复简短自然，不超过3句话
        5. 保留人格专属水印：{GLOBAL_CURRENT_PERSONALITY.get('watermark', '')}
        """
        # 加载对话历史（上下文）
        conversation_history = DB_MANAGER.get_conversation(user_id, limit=5) if DB_MANAGER.enable else USER_CONVERSATION_HISTORY.get(user_id, [])
        messages = [{"role": "system", "content": prompt}]
        for hist_time, hist_persona, hist_content in conversation_history:
            messages.append({"role": "user", "content": hist_content})

        # 12. 调用LLM生成回复
        llm_client = LLM_CLIENTS.get(current_persona_name, LLM_CLIENTS["default"])
        llm_reply = llm_client.generate_reply(messages)
        # 添加水印
        watermark = GLOBAL_CURRENT_PERSONALITY.get("watermark", "")
        final_reply = f"{llm_reply} {watermark}".strip()

        # 13. 多模态扩展（图片/语音）
        if "生成图片" in message or "画画" in message:
            image_prompt = message.replace("生成图片", "").replace("画画", "").strip()
            image_url = await self._generate_image(image_prompt, current_persona_name)
            if image_url:
                final_reply += f"\n{image_url}"
        if "语音回复" in message or "说出来" in message:
            voice_path = await self._generate_voice(final_reply, current_persona_name)
            if voice_path:
                await ctx.send_file(voice_path)  # 发送语音文件

        # 14. 发送回复并记录
        await ctx.send(final_reply)
        # 保存对话历史
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        DB_MANAGER.insert_conversation(user_id, time_str, current_persona_name, message)
        # 更新对话历史内存
        if not DB_MANAGER.enable:
            if user_id not in USER_CONVERSATION_HISTORY:
                USER_CONVERSATION_HISTORY[user_id] = []
            USER_CONVERSATION_HISTORY[user_id].append((time_str, current_persona_name, message))
        # 设置缓存
        self._set_cache(user_id, message, current_persona_name, final_reply)
        # 记录操作日志
        self._log_operation(user_id, "message.reply", f"成功：使用{current_persona_name}人格回复")

# 插件实例化
plugin = PersonalitySwitchPlugin()