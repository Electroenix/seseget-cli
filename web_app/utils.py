"""工具函数：在同步 Flask 路由中运行异步协程"""
import asyncio
import threading


# 后台事件循环（运行在独立线程中）
_loop: asyncio.AbstractEventLoop = None
_loop_thread: threading.Thread = None


def _start_background_loop():
    """在后台线程中启动事件循环"""
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """获取或创建后台事件循环"""
    global _loop, _loop_thread
    if _loop is None or _loop.is_closed():
        _loop_thread = threading.Thread(target=_start_background_loop, daemon=True)
        _loop_thread.start()
        # 等待循环启动
        import time
        while _loop is None:
            time.sleep(0.01)
    return _loop


def run_async(coro):
    """在同步上下文中运行异步协程，返回结果"""
    loop = get_or_create_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def shutdown_event_loop():
    """关闭后台事件循环"""
    global _loop
    if _loop and _loop.is_closed():
        return
    if _loop:
        _loop.call_soon_threadsafe(_loop.stop)
