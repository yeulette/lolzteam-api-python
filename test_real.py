from lolzteam import Forum, Market

TOKEN = "TOKEN"

# ── Forum ──────────────────────────────────────────
forum = Forum(token=TOKEN)

me = forum.users_get(user_id=2312422)  # получить пользователя с ID 1
print("Статус:", me.status_code)
print("Ответ:", me.json())

threads = forum.threads_list()
print("\nТемы:", threads.status_code, threads.json().keys())

# ── Market ─────────────────────────────────────────
market = Market(token=TOKEN)

profile = market.get_me()
print("\nМаркет профиль:", profile.status_code)
print(profile.json())

input()
