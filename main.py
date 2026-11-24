from machine import Pin, ADC, PWM
import time
import network
import urequests

# --- 1. Configuration Wi-Fi (Wokwi) ---
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""

# --- 2. Configuration ThingSpeak ---
THINGSPEAK_API_KEY = "HT8W129W9DBESWWQ" 
THINGSPEAK_URL = "http://api.thingspeak.com/update"

# --- # --- 3. Configuration des broches ---
piezo = ADC(Pin(34))          
piezo.atten(ADC.ATTN_11DB)    
batterie = ADC(Pin(32))       
batterie.atten(ADC.ATTN_11DB)
ldr = ADC(Pin(35))            
ldr.atten(ADC.ATTN_11DB)
led = PWM(Pin(2), freq=1000)  
led.duty(0)                   

# --- 4. Paramètres de logique ---
DELTA_THRESHOLD = 300         
DARK_THRESHOLD = 1000         # Ajusté à 1000 pour Wokwi
HOLD_TIME = 5                 
BATTERY_MIN = 1500            

last_piezo = 0
last_trigger_time = 0
last_status = ""

# --- 5. Fonctions ---
def connect_wifi():
    print("Connexion au Wi-Fi...", end="")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while not wlan.isconnected():
        time.sleep(0.5)
        print(".", end="")
    print("\nWi-Fi connecté ! IP:", wlan.ifconfig()[0])

def envoyer_donnees_thingspeak(ldr_val, bat_val, led_state, alerte_code):
    try:
        url = f"{THINGSPEAK_URL}?api_key={THINGSPEAK_API_KEY}&field1={ldr_val}&field2={bat_val}&field3={led_state}&field4={alerte_code}"
        response = urequests.get(url)
        print(f"📡 [ThingSpeak] Envoi OK (Code: {alerte_code}) - Status: {response.status_code}")
        response.close()
    except Exception as e:
        print("Erreur ThingSpeak:", e)

# --- 6. Démarrage ---
connect_wifi()
print("Système d'éclairage routier IoT démarré")

while True:
    ldr_val = ldr.read()
    piezo_val = piezo.read()
    bat_val = batterie.read() 
    
    delta = abs(piezo_val - last_piezo)
    last_piezo = piezo_val
    
    is_dark = ldr_val < DARK_THRESHOLD
    motion_detected = delta > DELTA_THRESHOLD
    has_energy = bat_val > BATTERY_MIN 
    
    now = time.time()
    current_status = ""
    alerte_code = 0 

    # --- LOGIQUE D'ÉCLAIRAGE ET D'ALERTE ---
    if not is_dark:
        led.duty(0)
        current_status = f"Jour (LDR={ldr_val}) : Lumiere eteinte"
        alerte_code = 0 
        
    elif not has_energy:
        led.duty(0)
        current_status = f"Nuit / Batterie FAIBLE ({bat_val}) : Lumiere eteinte"
        alerte_code = 2 
        
    elif motion_detected and has_energy:
        led.duty(1023)
        last_trigger_time = now
        current_status = f"Nuit + Mouvement + Batterie OK ({bat_val}) : Lumiere ALLUMEE"
        alerte_code = 1 
        
    elif now - last_trigger_time < HOLD_TIME and has_energy:
        current_status = f"Minuteur en cours ({int(HOLD_TIME - (now - last_trigger_time))}s) : Lumiere ALLUMEE"
        alerte_code = 1 
        
    else:
        led.duty(100)
        current_status = f"Nuit / Batterie OK ({bat_val}) / Pas de mouvement : VEILLE"
        alerte_code = 0 
    
    # --- AFFICHAGE LOCAL ET ENVOI CLOUD ---
    if current_status != last_status:
        print(current_status)
        last_status = current_status
        
        led_state = 1 if led.duty() > 500 else 0
        envoyer_donnees_thingspeak(ldr_val, bat_val, led_state, alerte_code)
        
    time.sleep_ms(50)