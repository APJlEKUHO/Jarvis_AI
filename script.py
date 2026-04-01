import datetime
import webbrowser
import os
import random


class Jarvis:
    def __init__(self):
        self.name = "Jarvis"
        self.commands = {
            "привет": self.hello,
            "время": self.time,
            "дата": self.date,
            "открой браузер": self.open_browser,
            "браузер": self.open_browser,
            "создай папку": self.create_folder,
            "случайное число": self.random_number,
            "команды": self.show_commands,
            "погода": self.weather,
            "выход": self.exit,
            "пх": self.pron,
            "порно": self.pron,
            "хентай": self.pron,
            "ютуб": self.yt,
        }

    def hello(self):
        return "Здравствуйте! Чем могу помочь?"

    def time(self):
        now = datetime.datetime.now()
        return f"Сейчас {now.strftime('%H:%M:%S')}"

    def pron(self):
        webbrowser.open("https://rt.pornhub.com")
        return "Открываю пх/порно/хентай"

    def yt(self):
        webbrowser.open("https://www.youtube.com")
        return "Открываю ютуб"

    def date(self):
        today = datetime.date.today()
        return f"Сегодня {today.strftime('%d.%m.%Y')}"

    def open_browser(self):
        webbrowser.open("https://www.yandex.ru")
        return "Открываю браузер"

    def create_folder(self):
        folder_name = input("Введите имя папки: ")
        try:
            os.mkdir(folder_name)
            return f"Папка '{folder_name}' создана"
        except FileExistsError:
            return "Папка уже существует"

    def random_number(self):
        return f"Случайное число: {random.randint(1, 100)}"

    def show_commands(self):
        return "Доступные команды: " + ", ".join(self.commands.keys())

    def weather(self):
        return "Для погоды нужен API. Добавьте позже через openweathermap.org"

    def exit(self):
        return "До свидания!"

    def run(self):
        print(f"{self.name} запущен. Введите 'команды' для списка команд.")

        while True:
            user_input = input("\nВаш запрос: ").lower().strip()

            if user_input in self.commands:
                result = self.commands[user_input]()
                print(result)

                if user_input == "выход":
                    break
            else:
                print("Команда не распознана. Введите 'команды' для списка.")


if __name__ == "__main__":
    assistant = Jarvis()
    assistant.run()