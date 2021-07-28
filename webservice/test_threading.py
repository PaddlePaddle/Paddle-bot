import threading

a_event = threading.Event()
b_event = threading.Event()
c_event = threading.Event()

def print_a(event, next_event):
    for i in range(10):
        event.wait()    # 等待时间触发
        print('a')
        event.clear()   # 内部标识设置为True,下一次循环进入阻塞状态
        next_event.set()


def print_b(event, next_event):
    for i in range(10):
        event.wait()
        print('b')
        event.clear()
        next_event.set()


def print_c(event, next_event):
    for i in range(10):
        event.wait()
        print('c')
        event.clear()
        next_event.set()

a_thread = threading.Thread(target=print_a, args=(a_event, b_event))
b_thread = threading.Thread(target=print_b, args=(b_event, c_event))
c_thread = threading.Thread(target=print_c, args=(c_event, a_event))

a_thread.start()
b_thread.start()
c_thread.start()

# 此时,所有的线程都处于阻塞状态
a_event.set()
