import os
import re
import random
import subprocess
import webbrowser
import datetime
import urllib.parse

import requests
import pyautogui
import pyttsx3
import speech_recognition as sr
import vlc
from dotenv import load_dotenv
from rapidfuzz import fuzz

load_dotenv()  # читает YANDEX_API_KEY и YANDEX_FOLDER_ID из файла .env (если он есть)

THRESHOLD = 85  # минимальная похожесть фразы (0-100), чтобы считать команду распознанной
MARGIN = 10     # если несколько фраз почти равны по баллу, выбираем более длинную (точнее)

# интент -> примерные фразы. Сравниваются с НАЧАЛОМ сказанного (столько слов, сколько во фразе),
# остаток фразы уходит обработчику как аргумент (что искать, какое приложение и т.д.)
INTENTS = {
    "greeting": ["привет", "здравствуй", "здравствуйте", "добрый день", "доброе утро"],
    "thanks": ["спасибо", "благодарю"],
    "goodbye": ["пока", "до свидания", "выключись", "отдыхай"],

    "open_app": ["открой", "запусти", "открыть", "запустить"],
    "youtube_open": ["включи ютуб", "зайди на ютуб", "перейди на ютуб", "открой youtube"],
    "youtube_search": ["найди на ютубе", "поищи на ютубе", "покажи на ютубе",
                       "включи на ютубе", "найди видео"],
    "search_web": ["найди", "поищи", "поиск", "гугл", "загугли", "найди в интернете"],
    "close_app": ["закрой окно", "закрой программу", "закрой приложение", "закрыть"],

    "time": ["сколько времени", "который час", "сколько время", "скажи время"],
    "date": ["какая дата", "какое сегодня число", "какой сегодня день"],

    "create_file": ["создай файл", "создай текстовый документ"],
    "create_folder": ["создай папку", "новая папка", "папка"],
    "copy": ["скопируй", "скопировать"],
    "paste": ["вставь", "вставить"],
    "screenshot": ["сделай скриншот", "скриншот", "сделай снимок экрана"],

    "music": ["включи музыку", "поставь музыку", "музыка", "включи песню", "поставь песню"],
    "stop_music": ["останови музыку", "выключи музыку", "стоп музыка"],
    "pause": ["пауза", "поставь на паузу"],
    "resume": ["продолжи", "продолжить", "продолжай"],
    "next": ["следующий трек", "следующий", "дальше"],
    "previous": ["предыдущий трек", "предыдущий"],

    "volume_up": ["громче", "сделай громче"],
    "volume_down": ["тише", "сделай тише"],
    "volume_set": ["громкость на максимум", "громкость на минимум", "громкость"],

    "shutdown": ["выключи компьютер", "выключи пк", "выключить компьютер"],
    "restart": ["перезагрузи компьютер", "перезагрузи пк", "перезагрузка"],
    "cancel_shutdown": ["отмена выключения", "отмени выключение"],
}

# название приложения -> (способ запуска, цель)
APPS = {
    "калькулятор": ("cmd", "calc"),
    "блокнот": ("cmd", "notepad"),
    "проводник": ("cmd", "explorer"),
    "хром": ("cmd", "chrome"),
    "браузер": ("cmd", "chrome"),
    "опера": ("cmd", "opera"),
    "файрфокс": ("cmd", "firefox"),
    "ворд": ("cmd", "winword"),
    "эксель": ("cmd", "excel"),
    "пауэрпоинт": ("cmd", "powerpnt"),
    "телеграм": ("cmd", "telegram"),
    "дискорд": ("cmd", "discord"),
    "стим": ("cmd", "steam"),
    "яндекс": ("url", "https://ya.ru"),
    "ютуб": ("url", "https://www.youtube.com"),
    "вк": ("url", "https://vk.com"),
    "спотифай": ("url", "https://open.spotify.com"),
    "видео": ("folder", "Videos"),
}

AUDIO_EXT = (".mp3", ".wav", ".flac")


def ask_yandex(question):
    """Возвращает текст ответа YandexGPT или None, если что-то пошло не так."""
    api_key = os.environ.get("YANDEX_API_KEY")
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    if not api_key or not folder_id:
        return None
    try:
        resp = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={"Authorization": f"Api-Key {api_key}", "x-folder-id": folder_id},
            json={
                "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
                "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 200},
                "messages": [
                    {"role": "system",
                     "text": "Ты голосовой ассистент Джарвис. Отвечай коротко, по-русски, не более двух предложений."},
                    {"role": "user", "text": question},
                ],
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"Ошибка Yandex API: {resp.status_code}")
            return None
        return resp.json()["result"]["alternatives"][0]["message"]["text"]
    except (requests.RequestException, KeyError, IndexError, ValueError) as e:
        print(f"Ошибка Yandex API: {e}")
        return None


class JarvisAssistant:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 180)
        self.engine.setProperty("volume", 0.9)
        try:
            for voice in self.engine.getProperty("voices"):
                if "russian" in voice.name.lower():
                    self.engine.setProperty("voice", voice.id)
                    break
        except Exception as e:
            print(f"Не удалось выбрать голос: {e}")

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        with self.microphone as source:  # калибровка шума один раз, а не на каждой фразе
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        self.hotword = "джарвис"
        self.running = True

        self.player = None
        self.playlist = []
        self.track_index = 0

        # интент -> метод. Два интента могут вести в один и тот же метод.
        self.commands = {
            "greeting": self.greet,
            "thanks": self.thank,
            "goodbye": self.goodbye,
            "open_app": self.open_app,
            "youtube_open": self.open_app,
            "youtube_search": self.youtube_search,
            "search_web": self.search_web,
            "close_app": self.close_app,
            "time": self.tell_time,
            "date": self.tell_date,
            "create_file": self.create_file,
            "create_folder": self.create_folder,
            "copy": self.copy_text,
            "paste": self.paste_text,
            "screenshot": self.take_screenshot,
            "music": self.play_music,
            "stop_music": self.stop_music,
            "pause": self.pause_media,
            "resume": self.resume_media,
            "next": self.next_track,
            "previous": self.previous_track,
            "volume_up": self.volume_up,
            "volume_down": self.volume_down,
            "volume_set": self.set_volume,
            "shutdown": self.shutdown_pc,
            "restart": self.restart_pc,
            "cancel_shutdown": self.cancel_shutdown,
        }
        print("Джарвис инициализирован. Говорите 'Джарвис' для активации...")

    # ---------- речь ----------
    def speak(self, text):
        print(f"Джарвис: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self):
        with self.microphone as source:
            print("Слушаю...")
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                return ""  # никто ничего не сказал, это не ошибка
        try:
            text = self.recognizer.recognize_google(audio, language="ru-RU").lower()
            print(f"Вы сказали: {text}")
            return text
        except sr.UnknownValueError:
            print("Не удалось распознать речь")
            return ""
        except sr.RequestError as e:
            print(f"Ошибка сервиса распознавания: {e}")
            return ""

    def confirm(self, question):
        self.speak(question)
        answer = self.listen().split()
        return any(w in answer for w in ("да", "подтверждаю", "давай"))

    # ---------- понимание команд ----------
    def detect_intent(self, text):
        """Возвращает (интент, остаток фразы) или (None, '')."""
        words = text.split()
        candidates = []
        for intent, phrases in INTENTS.items():
            for phrase in phrases:
                n = len(phrase.split())
                head = " ".join(words[:n])
                score = fuzz.ratio(head, phrase)
                if score >= THRESHOLD:
                    candidates.append((score, n, intent, " ".join(words[n:])))
        if not candidates:
            return None, ""
        top = max(c[0] for c in candidates)
        close = [c for c in candidates if c[0] >= top - MARGIN]
        _, _, intent, rest = max(close, key=lambda c: (c[1], c[0]))
        return intent, rest

    def process_command(self, text):
        if not text:
            return
        intent, rest = self.detect_intent(text)
        print(f"[интент: {intent}, аргумент: {rest!r}]")
        if intent is None:
            self.ai_response(text)
            return
        self.commands[intent](text, rest)

    def ai_response(self, question):
        answer = ask_yandex(question)
        if answer:
            self.speak(answer)
        else:
            self.speak("Поищу информацию в интернете")
            self.search_web(question, question)

    # ---------- простые ответы ----------
    def greet(self, command, rest=""):
        self.speak(random.choice(["Приветствую", "Здравствуйте", "Привет", "Рад вас слышать"]))

    def thank(self, command, rest=""):
        self.speak(random.choice(["Всегда пожалуйста", "Рад был помочь", "Обращайтесь"]))

    def goodbye(self, command, rest=""):
        self.speak("До свидания! Буду ждать вашего возвращения.")
        self.running = False

    def tell_time(self, command, rest=""):
        self.speak(f"Сейчас {datetime.datetime.now().strftime('%H:%M')}")

    def tell_date(self, command, rest=""):
        months = ["января", "февраля", "марта", "апреля", "мая", "июня",
                  "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        now = datetime.datetime.now()
        self.speak(f"Сегодня {now.day} {months[now.month - 1]} {now.year} года")

    # ---------- приложения и интернет ----------
    def open_app(self, command, rest=""):
        words = command.split()
        for name, (kind, target) in APPS.items():
            if not any(w.startswith(name) for w in words):
                continue
            try:
                if kind == "url":
                    webbrowser.open(target)
                elif kind == "folder":
                    path = os.path.join(os.path.expanduser("~"), target)
                    if not os.path.exists(path):
                        self.speak("Папка не найдена")
                        return
                    os.startfile(path)
                else:
                    result = subprocess.run(f'start "" {target}', shell=True, capture_output=True)
                    if result.returncode != 0:
                        self.speak(f"Не удалось открыть {name}")
                        return
                self.speak(f"Открываю {name}")
            except Exception as e:
                print(f"Ошибка: {e}")
                self.speak(f"Не удалось открыть {name}")
            return
        self.speak("Не удалось распознать приложение")

    def search_web(self, command, rest=""):
        if not rest:
            self.speak("Что именно нужно найти?")
            return
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(rest))
        self.speak(f"Ищу {rest}")

    def youtube_search(self, command, rest=""):
        if not rest:
            self.speak("Что искать на ютубе?")
            return
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(rest))
        self.speak(f"Ищу на ютубе {rest}")

    def close_app(self, command, rest=""):
        pyautogui.hotkey("alt", "f4")
        self.speak("Закрываю окно")

    # ---------- файлы и буфер ----------
    @staticmethod
    def safe_name(name, default):
        name = re.sub(r'[\\/:*?"<>|]', "", name).strip().strip(".")
        return name or default

    def create_file(self, command, rest=""):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"Новый документ_{stamp}.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write("Создано Джарвисом")
        self.speak(f"Создан файл {file_name}")

    def create_folder(self, command, rest=""):
        name = self.safe_name(re.sub(r"^назови\s*", "", rest), "Новая папка")
        os.makedirs(name, exist_ok=True)
        self.speak(f"Создана папка {name}")

    def copy_text(self, command, rest=""):
        pyautogui.hotkey("ctrl", "c")
        self.speak("Скопировано")

    def paste_text(self, command, rest=""):
        pyautogui.hotkey("ctrl", "v")
        self.speak("Вставлено")

    def take_screenshot(self, command, rest=""):
        filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot().save(filename)
        self.speak(f"Скриншот сохранён как {filename}")

    # ---------- музыка ----------
    def _play_current(self):
        if self.player:
            self.player.stop()
        self.player = vlc.MediaPlayer(self.playlist[self.track_index])
        self.player.play()

    def play_music(self, command, rest=""):
        folder = os.path.join(os.path.expanduser("~"), "Music")
        if not os.path.exists(folder):
            self.speak("Папка с музыкой не найдена")
            return
        files = [os.path.join(folder, f) for f in os.listdir(folder)
                 if f.lower().endswith(AUDIO_EXT)]
        if not files:
            self.speak("В папке с музыкой нет файлов")
            return
        random.shuffle(files)
        self.playlist, self.track_index = files, 0
        self._play_current()
        self.speak("Включаю музыку")

    def stop_music(self, command, rest=""):
        if self.player:
            self.player.stop()
            self.speak("Музыка остановлена")

    def pause_media(self, command, rest=""):
        if self.player:
            self.player.set_pause(1)
            self.speak("Пауза")

    def resume_media(self, command, rest=""):
        if self.player:
            self.player.play()
            self.speak("Продолжаю")

    def next_track(self, command, rest=""):
        if not self.playlist:
            self.speak("Музыка не играет")
            return
        self.track_index = (self.track_index + 1) % len(self.playlist)
        self._play_current()

    def previous_track(self, command, rest=""):
        if not self.playlist:
            self.speak("Музыка не играет")
            return
        self.track_index = (self.track_index - 1) % len(self.playlist)
        self._play_current()

    # ---------- громкость системы ----------
    def volume_up(self, command, rest=""):
        pyautogui.press("volumeup", presses=5)

    def volume_down(self, command, rest=""):
        pyautogui.press("volumedown", presses=5)

    def set_volume(self, command, rest=""):
        if "максимум" in command or "полную" in command:
            pyautogui.press("volumeup", presses=50)
        elif "минимум" in command:
            pyautogui.press("volumedown", presses=50)
        else:
            self.speak("Скажите: громкость на максимум или на минимум")

    # ---------- питание (с подтверждением и возможностью отмены, только Windows) ----------
    def shutdown_pc(self, command, rest=""):
        if self.confirm("Выключить компьютер? Скажите да"):
            os.system("shutdown /s /t 10")
            self.speak("Выключение через 10 секунд. Чтобы отменить, скажите: отмена выключения")
        else:
            self.speak("Отменено")

    def restart_pc(self, command, rest=""):
        if self.confirm("Перезагрузить компьютер? Скажите да"):
            os.system("shutdown /r /t 10")
            self.speak("Перезагрузка через 10 секунд. Чтобы отменить, скажите: отмена выключения")
        else:
            self.speak("Отменено")

    def cancel_shutdown(self, command, rest=""):
        os.system("shutdown /a")
        self.speak("Выключение отменено")

    # ---------- главный цикл ----------
    def extract_command(self, text):
        """Ищет хотворд с поправкой на ошибки распознавания.
        Возвращает остаток фразы или None, если хотворда нет."""
        words = text.split()
        for i, w in enumerate(words):
            if w == "jarvis" or fuzz.ratio(w, self.hotword) >= 70:
                return " ".join(words[:i] + words[i + 1:])
        return None

    def run(self):
        self.speak("Джарвис на связи! Чем могу помочь?")
        while self.running:
            try:
                text = self.listen()
                if not text:
                    continue
                command = self.extract_command(text)
                if command is None:
                    print("(хотворд не услышан)")
                    continue
                if not command:
                    self.speak("Слушаю")
                    command = self.listen()
                self.process_command(command)
            except KeyboardInterrupt:
                self.speak("Выключаюсь")
                self.running = False
            except Exception as e:
                print(f"Ошибка в основном цикле: {e}")


if __name__ == "__main__":
    JarvisAssistant().run()
