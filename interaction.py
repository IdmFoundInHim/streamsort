def notify_user(notification: str) -> None:
    print(notification)


def confirm_action(message: str) -> bool:
    return input(message)[0] in 'Yy'
