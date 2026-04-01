import datetime
import webbrowser
import os
import random
import subprocess
import time
import speech_recognition as sr
import sounddevice as sd
import numpy as np


class Jarvis:
    def __init__(self):
        self.name = "Jarvis"
        self.recognizer = sr.Recognizer()
        self.commands = {
            "привет": self.hello,
            "время": self.time,
            "дата": self.date,
            "открой браузер": self.open_browser,
            "открой браузер": self.open_browser,
            "создай папку": self.create_folder,
            "случайное число": self.random_number,
            "команды": self.show_commands,
            "погода": self.weather,
            "выход": self.exit,
            "открой пх": self.pron,
            "открой порно": self.pron,
            "открой хентай": self.pron,
            "открой ютуб": self.yt,
            "открой танки блиц": self.tanks_blitz,
            "открой танки бб": self.WOT
        }

    def hello(self):
        return "Здравствуйте! Чем могу помочь?"

    def time(self):
        now = datetime.datetime.now()
        return f"Сейчас {now.strftime('%H:%M:%S')}"

    def pron(self):
        webbrowser.open("https://rt.pornhub.com")
        return "Открываю пх/порно/хентай"

    def calc(self):
        subprocess.Popen('C:\\Windows\\System32\\calc.exe')
        return "Открываю калькулятор"

    def tanks_blitz(self):
        os.startfile("C:\\Games\\Tanki\\lgc_api.exe")
        time.sleep(10)
        os.startfile("C:\\Games\\Tanks_Blitz\\tanksblitz.exe")
        return "Открываю танки блиц"

    def WOT(self):
        os.startfile("C:\\Games\\Tanki\\lgc_api.exe")
        time.sleep(10)
        os.startfile("C:\\Games\\Tanki\\Tanki.exe")
        return "Открываю танки бб"


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

    def listen(self):
        fs = 16000
        duration = 4  # seconds
        print("Слушаю...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        audio_data = sr.AudioData(recording.tobytes(), fs, 2)
        try:
            text = self.recognizer.recognize_google(audio_data, language='ru-RU')
            return text.lower().strip()
        except sr.UnknownValueError:
            print("Не понял, повторите")
            return None
        except sr.RequestError:
            print("Ошибка сети")
            return None

    def run(self):
        print(f"{self.name} запущен. Говорите команды.")

        while True:
            user_input = self.listen()
            if user_input is None:
                continue

            if user_input in self.commands:
                result = self.commands[user_input]()
                print(result)

                if user_input == "выход":
                    break
            else:
                print("Команда не распознана. Скажи 'команды' для списка.")


if __name__ == "__main__":
    assistant = Jarvis()
    assistant.run()
