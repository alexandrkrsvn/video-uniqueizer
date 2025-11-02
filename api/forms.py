from django import forms

FORMAT_CHOICES = [
    ("1:1","1:1 (720x720)"),
    ("9:16","9:16 (720x1280)"),
    ("16:9","16:9 (1280x720)")
]
POS_CHOICES = [
    ("Случайная","Случайная"),
    ("верх-лево","верх-лево"),
    ("верх-центр","верх-центр"),
    ("верх-право","верх-право"),
    ("центр-лево","центр-лево"),
    ("центр-центр","центр-центр"),
    ("центр-право","центр-право"),
    ("низ-лево","низ-лево"),
    ("низ-центр","низ-центр"),
    ("низ-право","низ-право")
]
BADGE_BEHAVIOR = [
    ("Исчезновение","Исчезновение"),
    ("Луп до конца","Луп до конца"),
    ("Обрезать по короткому","Обрезать по короткому")
]

class JobForm(forms.Form):
    job_name = forms.CharField(label="Имя задачи", max_length=100, required=False, help_text="Если не указано, будет присвоен номер.")
    
    # Выбор источника данных
    use_yadisk = forms.BooleanField(label="Использовать Яндекс Диск", required=False, initial=False)
    input_folder = forms.CharField(label="Папка с исходными видео (локальная)", widget=forms.TextInput(attrs={"size":"80"}), required=False)
    input_yadisk_path = forms.CharField(label="Папка на Яндекс Диске с исходными видео", widget=forms.TextInput(attrs={"size":"80", "readonly":"readonly"}), required=False)
    output_folder = forms.CharField(label="Папка для вывода (локальная)", widget=forms.TextInput(attrs={"size":"80"}), required=False)
    output_yadisk_path = forms.CharField(label="Папка на Яндекс Диске для вывода", widget=forms.TextInput(attrs={"size":"80", "readonly":"readonly"}), required=False)
    fmt = forms.ChoiceField(label="Формат", choices=FORMAT_CHOICES, initial="9:16")
    copies = forms.IntegerField(label="Копий на файл", min_value=1, max_value=50, initial=3)

    text_enabled = forms.BooleanField(label="Добавить текст", required=False)
    text_content = forms.CharField(label="Текст", required=False, widget=forms.TextInput(attrs={"size":"80"}))
    text_font_from_yadisk = forms.BooleanField(label="Шрифт с Яндекс Диска", required=False)
    text_fontfile = forms.CharField(label="Шрифт (локальный путь)", required=False, widget=forms.TextInput(attrs={"size":"80"}))
    text_fontfile_yadisk = forms.CharField(label="Шрифт (Яндекс Диск)", required=False, widget=forms.TextInput(attrs={"size":"80", "readonly":"readonly"}))
    text_auto = forms.BooleanField(label="Авто размер", required=False, initial=True)
    text_level = forms.ChoiceField(label="Уровень", choices=[("Подпись","Подпись"),("Заголовок","Заголовок")], initial="Подпись")
    text_fontsize = forms.IntegerField(label="Размер", required=False, initial=24)
    text_position = forms.ChoiceField(label="Позиция текста", choices=POS_CHOICES, initial="Случайная")

    badge_enabled = forms.BooleanField(label="Добавить бейдж", required=False)
    badge_from_yadisk = forms.BooleanField(label="Бейдж с Яндекс Диска", required=False)
    badge_path = forms.CharField(label="Файл бейджа (локальный путь)", required=False, widget=forms.TextInput(attrs={"size":"80"}))
    badge_path_yadisk = forms.CharField(label="Файл бейджа (Яндекс Диск)", required=False, widget=forms.TextInput(attrs={"size":"80", "readonly":"readonly"}))
    badge_random_scale = forms.BooleanField(label="Случайный масштаб", required=False)
    badge_scale_percent = forms.IntegerField(label="Масштаб %", required=False, initial=30, min_value=10, max_value=80)
    badge_position = forms.ChoiceField(label="Позиция бейджа", choices=POS_CHOICES, initial="Случайная")
    badge_behavior = forms.ChoiceField(label="Поведение бейджа", choices=BADGE_BEHAVIOR, initial="Исчезновение")

    safe_mode = forms.BooleanField(label="Безопасный режим", required=False, initial=True)
    profile_strong = forms.BooleanField(label="Сильная уникализация", required=False)
    cut = forms.BooleanField(label="Микросрез", required=False)
    contrast = forms.BooleanField(label="Контраст", required=False, initial=True)
    color_shift = forms.BooleanField(label="Сдвиг оттенков", required=False)
    noise = forms.BooleanField(label="Шум", required=False)
    brightness_sat = forms.BooleanField(label="Яркость/насыщенность", required=False, initial=True)
    crop_edges = forms.BooleanField(label="Обрезка краёв", required=False)
    geom = forms.BooleanField(label="Геометрия", required=False, initial=True)
    time_mod = forms.BooleanField(label="Временная модуляция", required=False, initial=True)
    overlays = forms.BooleanField(label="Оверлеи", required=False, initial=True)
    codec_random = forms.BooleanField(label="Случайные параметры кодека", required=False, initial=True)
    color_mod = forms.BooleanField(label="Модуляция цвета", required=False)
    hidden_pattern = forms.BooleanField(label="Скрытый паттерн", required=False)

    # Можно зажать длительность “по шаблону”
    fixed_duration_enabled = forms.BooleanField(label="Фиксировать длительность", required=False)
    fixed_duration = forms.IntegerField(label="Длительность (сек)", required=False, min_value=1, max_value=600, initial=15)