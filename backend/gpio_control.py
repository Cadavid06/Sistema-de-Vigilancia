import RPi.GPIO as GPIO

# Configuración de pines
LED_VERDE_PIN = 23
LED_ROJO_PIN = 24

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LED_VERDE_PIN, GPIO.OUT)
GPIO.setup(LED_ROJO_PIN, GPIO.OUT)

def encender_verde():
    GPIO.output(LED_VERDE_PIN, GPIO.HIGH)

def apagar_verde():
    GPIO.output(LED_VERDE_PIN, GPIO.LOW)

def encender_rojo():
    GPIO.output(LED_ROJO_PIN, GPIO.HIGH)

def apagar_rojo():
    GPIO.output(LED_ROJO_PIN, GPIO.LOW)

def limpiar():
    GPIO.cleanup()
