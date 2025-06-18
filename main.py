import requests
import time
import csv

# Funkcja zwraca URL'e do endpointów z których pobrać można wszystkie partie gracza z każdego miesiąca w którym zagrał chociaż jedną partię
def download_archives(username):
    url = f"https://api.chess.com/pub/player/{username}/games/archives" # Endpoint URL
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}) # Header; bez headera API zwróci brak dostępu (403)
    if res.status_code == 200:
        return res.json()["archives"][::-1]
    else:
        raise Exception(f"Error downloading archives: {res.status_code}")

# Pobiera wszystkie partie gracza o danym nicku i zwraca je jako osobne elementy tablicy. Opcjonalne argumenty to time_control: określa tempo jakim grane miały być gry które mają zostać zwrócone, oraz delay: zmiana opóźnienia
# które ma zapobiec throttlingowi oraz tymczasowym banom    
def pobierz_wszystkie_partie(username, time_control=None, delay=1.0):
    archives = download_archives(username) # Pobiera "archiwa" - wytłumaczenie czym są jest nad użytą funkcją
    all_games = [] # Utworzenie listy wszystkich gier

    for url in archives:
        print(f"Downloading: {url}")
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}) # Header; bez headera API zwróci brak dostępu (403)
        if res.status_code != 200:
            print(f"Error {res.status_code} at {url}") # Błąd pobierania
            continue

        dane = res.json().get("games", []) # Ściągnięcie wszystkich gier z danego URL (miesiąc/rok) do tablicy jako osobne jej elementy
        for game in dane:
            if time_control is None or game.get("time_class") == time_control: # Sprawdzenie zgodności danej gry z pożądanym tempem (np. blitz, rapid)
                all_games.append(game) # Dodanie do listy wszystkich gier

        time.sleep(delay) # Zapobiega nadużyciom i tymczasowym banom

    return all_games

# Funkcja zwraca kod kraju z jakiego pochodzi użytkownik. Argumentem jest odpowiedni link API z nazwą gracza
def download_country(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        return "?"
    data = res.json()
    country = data.get("country")
    return country.split("/")[-1] if country else "?"


def numeric_score(result_str):
    # Niestety chess.com nie zwraca bezpośrednio wyniku jako punkty, więc trzeba wydedukować go na podstawie odpowiednich opisów.
    draws = ["stalemate", "agreed", "repetition", "insufficient", "timevsinsufficient", "50move", "threecheckdraw"]
    loses = ["checkmated", "timeout", "resigned", "abandoned", "lose"]
    
    if result_str == "win":
        return 1
    elif result_str in draws:
        return 0.5
    elif result_str in loses:
        return 0
    else:
        return "?"

# Zapisuje statystyki gracza do pliku CSV. Na jego podstawie można przeprowadzić dalsze "analizy" i "statystyki"
def save_stats_to_csv(username, games, filename="statystyki.csv"):
    with open(filename, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(["Date", "Color", "Opponent", "Score", "Player rating before match", "Opponent rating before match", "Time control", "Country", "Rating difference"])
        i = 1
        for game in games:
            color = "white" if game["white"]["username"].lower() == username.lower() else "black"
            opponent = game["black"]["username"] if color == "white" else game["white"]["username"]
            score = game["white"]["result"] if color == "white" else game["black"]["result"]
            score = numeric_score(score)
            my_rating = game[color]["rating"]
            opponent_rating = game["black"]["rating"] if color == "white" else game["white"]["rating"]
            data = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(game["end_time"]))
            time_control = game["time_class"]
            if color == "white":
                link = game["black"]["@id"]
            else:
                link = game["white"]["@id"]
            country = download_country(link)
            time.sleep(0.1) # Tu minimalne opóźnienie - te endpointy dopuszczają szybsze zapytania
            print(str(link) + ': ' + str(country) + ' (' + str(i) + '/' + str(len(games)) + ')')
            i += 1
            diff = opponent_rating - my_rating
            writer.writerow([data, color, opponent, score, my_rating, opponent_rating, time_control, country, diff])

if __name__ == "__main__":
    name = str(input('Podaj nick: '))
    games = pobierz_wszystkie_partie(name)

    print(f"Found {len(games)} games.")

    with open(name + ".pgn", "w", encoding="utf-8") as f:
        for gra in games:
            f.write(gra["pgn"] + "\n\n")
                
    save_stats_to_csv(name, games, name+"_stats.csv")
        
