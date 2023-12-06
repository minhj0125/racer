import time
import random
import board
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw
from adafruit_rgb_display import st7789

class Joystick:
    def __init__(self):
        self.cs_pin = DigitalInOut(board.CE0)
        self.dc_pin = DigitalInOut(board.D25)
        self.reset_pin = DigitalInOut(board.D24)
        self.BAUDRATE = 24000000

        self.spi = board.SPI()
        self.disp = st7789.ST7789(
            self.spi,
            height=240,
            y_offset=80,
            rotation=180,
            cs=self.cs_pin,
            dc=self.dc_pin,
            rst=self.reset_pin,
            baudrate=self.BAUDRATE,
        )

        # Input pins:
        self.button_L = DigitalInOut(board.D27)
        self.button_L.direction = Direction.INPUT
        self.button_L.pull = Pull.UP

        self.button_R = DigitalInOut(board.D23)
        self.button_R.direction = Direction.INPUT
        self.button_R.pull = Pull.UP

joystick = Joystick()

class Obstacle:
    def __init__(self, width, height, speed):
        self.width = width
        self.height = height
        self.speed = speed
        self.x = random.randint(0, joystick.disp.width - self.width)
        self.y = -self.height - 40  # 초기 위치
        self.image = Image.open('racer/mercedes.png').convert('RGBA').resize((24,55))

    def update(self):
        self.y += self.speed

    def draw(self, image):
        obstacle_mask = self.image.split()[3]
        image.paste(self.image, (int(self.x), int(self.y)), obstacle_mask)

    def collides_with(self, other):
        return (
            self.x < other.x + other.width and
            self.x + self.width > other.x and
            self.y < other.y + other.height and
            self.y + self.height > other.y
        )

class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.obstacle_width = 20
        self.obstacle_height = 50
        self.car_width = 20
        self.car_height = 50
        self.car_x = width // 2 - self.car_width // 2
        self.car_y = height - self.car_height - 10
        self.car_speed = 0
        self.car_acceleration = 2  # 가속도
        self.car_max_speed = 15  # 최대 속도
        self.obstacles = []
        self.last_obstacle_time = time.monotonic()
        self.car_image = Image.open('racer/ferrari.png').convert('RGBA').resize((24, 55))

    def spawn_obstacle(self):
        if time.monotonic() - self.last_obstacle_time > 3: 
            num_obstacles = random.randint(1, 2)  # 임의의 개수로 장애물 생성
            for _ in range(num_obstacles):
                obstacle_speed = random.uniform(3, 7)  # 장애물 속도를 랜덤하게 설정
                new_obstacle = Obstacle(self.obstacle_width, self.obstacle_height, obstacle_speed)
                if not any(new_obstacle.collides_with(other) for other in self.obstacles):
                    self.obstacles.append(new_obstacle)
            self.last_obstacle_time = time.monotonic()

    def update(self):
        for obstacle in self.obstacles:
            obstacle.update()
            if obstacle.y > self.height:
                self.obstacles.remove(obstacle)
        self.spawn_obstacle()

    def check_collision(self):
        for obstacle in self.obstacles:
            if (
                self.car_x < obstacle.x + obstacle.width
                and self.car_x + self.car_width > obstacle.x
                and self.car_y < obstacle.y + obstacle.height
                and self.car_y + self.car_height > obstacle.y
            ):
                return True
        return False

    def update_car_position(self):
        if not joystick.button_L.value:  # Left button pressed
            self.car_speed -= self.car_acceleration
        elif not joystick.button_R.value:  # Right button pressed
            self.car_speed += self.car_acceleration
        else:
            self.car_speed *= 0.8

        # Limit the car speed to the maximum speed
        self.car_speed = max(-self.car_max_speed, min(self.car_max_speed, self.car_speed))

        # Update the car position based on the current speed
        self.car_x += self.car_speed

        # Ensure the car stays within the screen bounds
        self.car_x = max(0, min(self.width - self.car_width, self.car_x))

    def draw_obstacles(self, draw):
        for obstacle in self.obstacles:
            obstacle.draw(draw)

    def draw_car(self, image):
        # Create a mask from the alpha channel of the car image
        car_mask = self.car_image.split()[3]

        # Paste the car image onto the background using the alpha channel as the mask
        image.paste(self.car_image, (int(self.car_x), int(self.car_y)), car_mask)

# 게임 초기화
game = Game(joystick.disp.width, joystick.disp.height)

background_image = Image.open('racer/circuit.png').resize((joystick.disp.width, joystick.disp.height)).convert('RGBA')

score = 0

# 메인 루프
while True:
    command = None
    game.update_car_position()
    game.update()

    # Check for collision
    if game.check_collision():
        print("Game Over! Score:", score)
        break

    # Draw everything
    my_image = background_image.copy()

    game.draw_car(my_image)
    game.draw_obstacles(my_image)

    joystick.disp.image(my_image)
    time.sleep(0.001)  # 시간을 조절하여 게임 속도를 조절할 수 있습니다.
    #joystick.disp.image(Image.new("RGB", (joystick.disp.width, joystick.disp.height)))  # Clear the display
    score += 1
