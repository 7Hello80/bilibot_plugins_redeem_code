import plugin_dev
import json
import os

class Plugin(plugin_dev.PluginBase):
    def __init__(self, bot_manager=None, config_manager=None, plugin_config=None):
        super().__init__(bot_manager, config_manager, plugin_config)
        self.version = "1.0.0"
        self.codes_file = os.path.join(os.path.dirname(__file__), "codes.json")
        self.codes = []
        self.load_codes()
        
        # 创建用户计数表
        self.database.create_table('user_redeem_count', {
            'user_id': 'INTEGER PRIMARY KEY',
            'count': 'INTEGER DEFAULT 0',
            'last_redeem_time': 'INTEGER'
        })
        
        # 注册消息处理器
        self.register_message_handler(self.handle_redeem_message)
    
    def on_load(self):
        """插件加载时调用"""
        self.logger.info("优惠码插件加载成功")
        self.logger.info(f"已加载 {len(self.codes)} 个优惠码")
    
    def on_unload(self):
        """插件卸载时调用"""
        self.save_codes()
        self.logger.info("优惠码插件卸载成功")
    
    def load_codes(self):
        """加载优惠码"""
        try:
            if os.path.exists(self.codes_file):
                with open(self.codes_file, 'r', encoding='utf-8') as f:
                    self.codes = json.load(f)
                self.logger.info(f"成功加载 {len(self.codes)} 个优惠码")
            else:
                self.logger.warning("优惠码文件不存在，使用空列表")
                self.codes = []
        except Exception as e:
            self.logger.error(f"加载优惠码失败: {str(e)}")
            self.codes = []
    
    def save_codes(self):
        """保存优惠码"""
        try:
            with open(self.codes_file, 'w', encoding='utf-8') as f:
                json.dump(self.codes, f, indent=2, ensure_ascii=False)
            self.logger.info("优惠码保存成功")
        except Exception as e:
            self.logger.error(f"保存优惠码失败: {str(e)}")
    
    def get_user_redeem_count(self, user_id):
        """获取用户兑换次数"""
        result = self.database.fetch_one(
            "SELECT count FROM user_redeem_count WHERE user_id = ?", 
            (user_id,)
        )
        return result[0] if result else 0
    
    def increment_user_redeem_count(self, user_id):
        """增加用户兑换次数"""
        current_count = self.get_user_redeem_count(user_id)
        import time
        current_time = int(time.time())
        
        if current_count == 0:
            # 插入新记录
            self.database.execute(
                "INSERT INTO user_redeem_count (user_id, count, last_redeem_time) VALUES (?, 1, ?)",
                (user_id, current_time)
            )
        else:
            # 更新现有记录
            self.database.execute(
                "UPDATE user_redeem_count SET count = count + 1, last_redeem_time = ? WHERE user_id = ?",
                (current_time, user_id)
            )
        
        return current_count + 1
    
    def get_available_code(self):
        """获取一个可用的优惠码"""
        for code in self.codes:
            if not code.get("is_send", False):
                return code
        return None
    
    def mark_code_as_sent(self, code_name):
        """标记优惠码为已发送"""
        for code in self.codes:
            if code.get("name") == code_name:
                code["is_send"] = True
                self.save_codes()
                return True
        return False
    
    def handle_redeem_message(self, message_data):
        """处理优惠码消息"""
        content = message_data.get('content', '').strip()
        sender_uid = message_data.get('sender_uid')
        
        # 检查是否包含关键词"优惠码"
        if "优惠码" not in content:
            return None
        
        self.logger.info(f"用户 {sender_uid} 请求优惠码")
        
        # 获取用户当前兑换次数
        current_count = self.get_user_redeem_count(sender_uid)
        
        if current_count >= 1:
            self.logger.info(f"用户 {sender_uid} 已达到最大兑换次数 ({current_count})")
            return "免费优惠码只能领取 1 次。"
        
        # 获取可用优惠码
        available_code = self.get_available_code()
        if not available_code:
            self.logger.warning("没有可用的优惠码了")
            return "抱歉，优惠码已发放完毕。"
        
        # 增加用户计数
        new_count = self.increment_user_redeem_count(sender_uid)
        
        # 标记优惠码为已发送
        code_name = available_code["name"]
        self.mark_code_as_sent(code_name)
        
        self.logger.info(f"向用户 {sender_uid} 发放优惠码: {code_name} (第{new_count}次)")
        
        # 返回回复
        return f"这是优惠码：{code_name}"