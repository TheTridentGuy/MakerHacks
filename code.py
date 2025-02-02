# type: ignore
import time
import wifi
import socketpool
import digitalio
import board
import pwmio
from digitalio import Direction
from digitalio import DigitalInOut as dio
from pwmio import PWMOut as pwm
from adafruit_httpserver import Server, Request, Response
from adafruit_motor import servo
from config import AP_SSID, AP_PASSWORD 
import adafruit_hcsr04

wifi.radio.start_ap(ssid=AP_SSID, password=AP_PASSWORD)
wifi.radio.start_dhcp_ap()
wifi.radio.hostname = "esp32"

print(f"started ap: ssid: '{AP_SSID}', password: '{AP_PASSWORD}'")
print(f"address(es): {",".join(wifi.radio.addresses_ap)}")

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/static", debug=True)

laser = dio(board.D15)
laser.direction = Direction.OUTPUT
red = pwm(board.D2, frequency=5000, duty_cycle=0)
green = pwm(board.D4, frequency=5000, duty_cycle=0)
blue = pwm(board.RX2, frequency=5000, duty_cycle=0)
servo1_pwm = pwm(board.D18, frequency=50)
servo1 = servo.Servo(servo1_pwm)
servo2_pwm = pwm(board.D19, frequency=50)
servo2 = servo.Servo(servo2_pwm)
servo1.angle = 90
servo2.angle = 90
sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.TX2, echo_pin=board.D5)


def set_rgb(r, g, b):
    r = int(r * (65535/255))
    g = int(g * (65535/255))
    b = int(b * (65535/255))
    red.duty_cycle = r
    green.duty_cycle = g
    blue.duty_cycle = b


@server.route("/")
def base(request):
    return Response(request, open("templates/index.html", "r").read(), content_type="text/html")


@server.route("/laser/toggle")
def base(request):
    laser.value = not laser.value
    return Response(request, "laser toggled")


@server.route("/rgb/set")
def rgb_set(request):
    color = request.query_params.get("color")
    print(request.query_params)
    print("color", color)
    r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    set_rgb(r, g, b)
    return Response(request, f"set rgb {r}, {g}, {b}")


@server.route("/sonar/get")
def sonar_dist(request):
    return Response(request, str(sonar.distance))


@server.route("/arm/toggle")
def arm_toggle(request):
    global armed, last_dist
    armed = not armed
    if armed:
        set_rgb(255, 0, 0)
        servo1.angle = 90
        servo2.angle = 90
    else:
        set_rgb(0, 255, 0)
    while True:
        try:
            last_dist = sonar.distance
            print(last_dist)
            break
        except RuntimeError:
            pass
    return Response(request, str(armed))


armed = False
last_dist = 0


set_rgb(0, 255, 0)
server.start(str(wifi.radio.addresses_ap[0]), 80)
while True:
    try:
        server.poll()
    except Exception as e:
        print(e)
    if armed:
        try:
            dist = sonar.distance
        except RuntimeError:
            dist = 0
        if abs(last_dist - dist) > 10:
            set_rgb(0, 0, 255)
            servo1.angle = 0
            servo2.angle = 180
