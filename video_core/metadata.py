import random
import datetime

def random_metadata() -> list:
    now = datetime.datetime.now()
    random_days = random.randint(-365, 0)
    creation_time = now + datetime.timedelta(days=random_days)
    year = creation_time.year

    devices = [
        ("Canon", "EOS R5"), ("Sony", "Alpha 7 IV"), ("Apple", "iPhone 16 Pro Max"),
        ("Samsung", "Galaxy S25 Ultra"), ("DJI", "Pocket 3"), ("GoPro", "Hero 12"),
        ("Huawei", "Pura 70 Ultra"), ("Google", "Pixel 9 Pro XL"), ("Xiaomi", "15 Ultra"),
        ("Oppo", "Find X8 Ultra"), ("Vivo", "X200 Ultra"), ("Sony", "Xperia 1 VII"),
        ("Panasonic", "Lumix GH6"), ("Nikon", "Z6 II"), ("Fujifilm", "X-T5"),
        ("Blackmagic", "Pocket Cinema Camera 6K"), ("Red", "Komodo"), ("Arri", "Alexa Mini")
    ]
    make, model = random.choice(devices)

    encoders = [
        f"Lavf{random.randint(57, 60)}.{random.randint(0, 100)}.{random.randint(0, 100)}",
        f"FFmpeg {random.randint(5, 7)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        f"x264 core {random.randint(140, 164)} r{random.randint(2800, 3100)}",
        f"HandBrake {random.randint(1, 2)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        f"Adobe Media Encoder {random.randint(2023, 2025)}.{random.randint(1, 5)}",
        f"libx265 - crf {random.randint(18, 28)}",
        f"AV1 Encoder {random.randint(1, 3)}.{random.randint(0, 9)}",
        f"VP9 Encoder",
        f"ProRes 422 HQ",
        f"MPEG-4 Visual"
    ]
    encoder = random.choice(encoders)

    comments = [
        "Shot on my phone during vacation", "Fun moment with friends", "Quick capture at the event",
        "Family gathering video", "Birthday party highlights", "Test footage from new camera",
        "Nature walk recording", "City exploration clip", "Home video memory", "Adventure trip snippet",
        "Concert footage", "Sports event capture", "Cooking tutorial", "DIY project video",
        "Travel vlog entry", "Pet playing moment", "Sunset timelapse", "Workout session record"
    ]
    comment = random.choice(comments)

    artists = [
        "AlexV", "SkyCam", "VlogStar", "JohnDoeFilms", "JaneSmithMedia", "TechReviewer",
        "AdventureSeeker", "NatureLover", "CityExplorer", "FamilyMoments", "MusicFanatic",
        "SportsEnthusiast", "FoodieChef", "DIYMaster", "TravelBlogger", "PetOwner", 
        "PhotographyPro", "VideoEditorGuy", "CreativeArtist", "DailyVlogger"
    ]
    artist = random.choice(artists)

    genres = [
        "Home Video", "Vlog", "Tutorial", "Documentary", "Short Film", "Music Video",
        "Sports", "Travel", "Nature", "Comedy", "Action", "Drama", "Educational",
        "Review", "Unboxing", "Gaming", "Cooking"
    ]
    genre = random.choice(genres)

    titles = [
        f"{random.choice(['Clip', 'Video', 'Recording', 'Footage', 'Capture', 'Moment'])} {random.randint(1000, 99999)}",
        f"{random.choice(comments).split()[0]} {random.choice(['Video', 'Clip', 'Record'])} {random.randint(1, 1000)}",
        f"Untitled {random.randint(1, 500)}",
        f"IMG_{random.randint(1000, 9999)}_VID",
        f"DSC{random.randint(10000, 99999)}"
    ]
    title = random.choice(titles)

    descriptions = [
        f"{comment}. Recorded using {make} {model}.",
        f"A short video of {comment.lower()}. Edited with {encoder.split()[0]}.",
        f"{genre} video: {comment}",
        f"Captured on {creation_time.strftime('%Y-%m-%d')}. {comment}",
        f"By {artist}: {comment}"
    ]
    description = random.choice(descriptions)

    softwares = [
        f"Adobe Premiere Pro {random.randint(2023, 2025)}",
        f"Final Cut Pro {random.randint(10, 12)}.{random.randint(0, 9)}",
        f"DaVinci Resolve {random.randint(17, 19)}",
        f"iMovie {random.randint(10, 12)}",
        f"Windows Movie Maker",
        f"CapCut {random.randint(1, 3)}.{random.randint(0, 9)}",
        f"Kdenlive {random.randint(20, 25)}.{random.randint(0, 12)}.{random.randint(0, 31)}"
    ]
    software = random.choice(softwares)

    metadata = [
        "-metadata", f"title={title}",
        "-metadata", f"encoder={encoder}",
        "-metadata", f"artist={artist}",
        "-metadata", f"comment={comment}",
        "-metadata", f"make={make}",
        "-metadata", f"model={model}",
        "-metadata", f"creation_time={creation_time.isoformat()}",
        "-metadata", f"genre={genre}",
        "-metadata", f"description={description}",
        "-metadata", f"year={year}",
        "-metadata", f"software={software}",
        "-metadata", f"copyright=Copyright {year} {artist}",
    ]

    extra_tags = [
        ("publisher", random.choice(["YouTube", "Vimeo", "Personal", "Stock Footage"])),
        ("album", random.choice(["My Videos", "Collection 2025", "Random Clips"])),
        ("track", f"{random.randint(1, 20)}/{random.randint(20, 100)}"),
        ("duration", f"{random.uniform(10, 600):.2f}"),
    ]
    for key, value in random.sample(extra_tags, k=random.randint(1, len(extra_tags))):
        metadata.extend(["-metadata", f"{key}={value}"])

    return metadata


