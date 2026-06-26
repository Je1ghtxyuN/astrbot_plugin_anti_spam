import time
from collections import defaultdict, deque

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star


class AntiSpamPlugin(Star):
    """反刷屏插件"""

    def __init__(self, context: Context):
        super().__init__(context)

        config = context.get_config()
        self.enabled = config.get("enabled", True)
        self.duplicate_threshold = config.get("duplicate_threshold", 3)
        self.duplicate_window = config.get("duplicate_window_seconds", 10)
        self.flood_threshold = config.get("flood_threshold", 5)
        self.flood_window = config.get("flood_window_seconds", 10)
        self.cooldown_seconds = config.get("cooldown_seconds", 30)

        # Per-user tracking state (in-memory, resets on restart)
        self._duplicate_tracker: dict[str, deque] = defaultdict(deque)
        self._flood_tracker: dict[str, deque] = defaultdict(deque)
        self._cooldowns: dict[str, float] = {}

        # Periodic cleanup counter
        self._msg_count = 0
        self._cleanup_interval = 200

        logger.info(
            f"[AntiSpam] v1.0.1 已加载 | "
            f"重复: {self.duplicate_threshold}次/{self.duplicate_window}s | "
            f"刷屏: {self.flood_threshold}条/{self.flood_window}s | "
            f"冷却: {self.cooldown_seconds}s"
        )

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def anti_spam_handler(self, event: AstrMessageEvent):
        """反刷屏主处理器：检测重复消息和刷屏行为，触发冷却时阻断事件传播以避免 token 消耗。"""
        if not self.enabled:
            return

        # 只处理真实聊天消息，跳过撤回通知、系统事件等非聊天事件
        if not self._is_chat_message(event):
            return

        user_id = str(event.get_sender_id())
        if not user_id:
            return

        now = time.time()

        # Periodic cleanup
        self._msg_count += 1
        if self._msg_count >= self._cleanup_interval:
            self._msg_count = 0
            self._cleanup_expired(now)

        # Cooldown check — silently drop if user is in cooldown
        if user_id in self._cooldowns:
            if now < self._cooldowns[user_id]:
                event.stop_event()
                return
            else:
                del self._cooldowns[user_id]

        # Flood detection
        flood_deque = self._flood_tracker[user_id]
        flood_deque.append(now)
        while flood_deque and now - flood_deque[0] > self.flood_window:
            flood_deque.popleft()

        if len(flood_deque) >= self.flood_threshold:
            self._trigger_cooldown(user_id, now, event, reason="flood")
            return

        # Duplicate detection (text messages only — images/stickers have empty get_message_str())
        msg_text = event.get_message_str()
        if msg_text:
            dup_deque = self._duplicate_tracker[user_id]
            dup_deque.append((now, msg_text))
            while dup_deque and now - dup_deque[0][0] > self.duplicate_window:
                dup_deque.popleft()

            dup_count = sum(1 for _, text in dup_deque if text == msg_text)
            if dup_count >= self.duplicate_threshold:
                self._trigger_cooldown(user_id, now, event, reason="duplicate")
                return

        # No spam — let event continue to next handler / LLM

    def _trigger_cooldown(
        self, user_id: str, now: float, event: AstrMessageEvent, reason: str
    ):
        self._cooldowns[user_id] = now + self.cooldown_seconds
        self._duplicate_tracker.pop(user_id, None)
        self._flood_tracker.pop(user_id, None)

        logger.info(
            f"[AntiSpam] {reason} 触发 | 用户: {user_id} | 冷却: {self.cooldown_seconds}s"
        )

        # 私聊发送警告，群聊静默丢弃
        if event.is_private_chat():
            event.set_result(event.plain_result("检测到刷屏行为，你的消息将被暂时忽略。"))
        event.stop_event()

    @staticmethod
    def _is_chat_message(event: AstrMessageEvent) -> bool:
        """判断是否为真实聊天消息，排除撤回通知、系统事件等。"""
        message = event.get_messages()
        if not message:
            return False

        # 检查是否有实际内容的消息段（文本、图片、表情等）
        from astrbot.api.message_components import Plain, Image, Face, At, Reply, Forward
        content_types = (Plain, Image, Face, At, Reply, Forward)

        for seg in message:
            if isinstance(seg, content_types):
                # Plain 段需要有实际文本内容
                if isinstance(seg, Plain) and not seg.text.strip():
                    continue
                return True

        return False

    def _cleanup_expired(self, now: float):
        expired = [uid for uid, end in self._cooldowns.items() if now >= end]
        for uid in expired:
            del self._cooldowns[uid]

        max_window = max(self.duplicate_window, self.flood_window)
        stale = [
            uid
            for uid, dq in self._flood_tracker.items()
            if not dq or now - dq[-1] > max_window * 2
        ]
        for uid in stale:
            self._flood_tracker.pop(uid, None)
            self._duplicate_tracker.pop(uid, None)

        if expired or stale:
            logger.debug(f"[AntiSpam] 清理: {len(expired)} 冷却, {len(stale)} 过期追踪")

    async def terminate(self):
        """插件卸载/停用时清理内存状态。"""
        self._duplicate_tracker.clear()
        self._flood_tracker.clear()
        self._cooldowns.clear()
        logger.info("[AntiSpam] 已卸载，内存状态已清理")
