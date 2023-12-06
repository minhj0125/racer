import time
import random
import board
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont
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

        self.button_R = DigitalInOut(board.D23)
        self.button_R.direction = Direction.INPUT

        self.button_A = DigitalInOut(board.D5)  
        self.button_A.direction = Direction.INPUT

        self.button_B = DigitalInOut(board.D6)
        self.button_B.direction = Direction.INPUT

        # Turn on the Backlight
        self.backlight = DigitalInOut(board.D26)
        self.backlight.switch_to_output()
        self.backlight.value = True


joystick = Joystick()

class Obstacle:
    def __init__(self, width, height, speed):
        self.width = width
        self.height = height
        self.speed = speed
        self.x = random.randint(0, joystick.disp.width - self.width)
        self.y = -self.height - 100
        image_choice = random.choice(['racer/mercedes.png', 'racer/mclaren.png'])
        self.image = Image.open(image_choice).convert('RGBA').resize((24, 55))

        self.x_speed = random.uniform(-5, 5) #좌우로
        self.x_acceleration = 0

    def update(self):
        self.y += self.speed
        self.x += self.x_speed

        # 화면 끝에서 방향 변경
        if self.x <= 0 or self.x >= joystick.disp.width - self.width:
            self.x_speed = -self.x_speed

        self.x_acceleration = random.uniform(-0.1, 0.1)
        self.x_speed += self.x_acceleration

        # 속도 제한
        self.x_speed = max(-5, min(5, self.x_speed))
        
    def draw(self, image):
        obstacle_mask = self.image.split()[3]
        image.paste(self.image, (int(self.x), int(self.y)), obstacle_mask)

    def collides_with(self, other): #충돌 감지 여유 
        buffer = 5  
        return (
            self.x + buffer < other.x + other.width - buffer and
            self.x + self.width - buffer > other.x + buffer and
            self.y + buffer < other.y + other.height - buffer and
            self.y + self.height - buffer > other.y + buffer
        )
    
class ShieldItem:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.active = False  # 방어막 활성화?
        self.duration = 5  # 방어막 지속
        self.activation_time = 0  # 방어막 활성화
        self.spawn_time = 0  
        self.spawn_interval = random.randint(20, 30)  # 방어막 생성 간격
        self.spawn_speed = 7
        self.count = 0  # 방어막 카운트
        self.image = Image.open('racer/shield.png').convert('RGBA').resize((15, 18))
        self.x = 0 
        self.y = 0  

    def draw(self, image):
        shield_mask = self.image.split()[3]
        image.paste(self.image, (int(self.x), int(self.y)), shield_mask)

    def spawn(self):
        self.active = True
        self.activation_time = time.monotonic()
        self.spawn_time = time.monotonic()
        self.x = random.randint(0, game.width - self.width)  # 랜덤으로 생성
        self.y = -20

    def collides_with(self, other):  # 방어막 먹기
        return (
            self.x < other.car_x + other.car_width and
            self.x + self.width > other.car_x and
            self.y < other.car_y + other.car_height and
            self.y + self.height > other.car_y
        )

    def update(self): 
        if self.active:
            self.y += self.spawn_speed

    def collect(self):
        self.active = False
        self.count += 1  # 방어막 카운트 +1

    def use(self):
        if self.count > 0:
            self.active = True
            self.activation_time = time.monotonic()
            self.count -= 1  # 방어막 사용시 카운트 업데이트

    def is_active(self):
        return self.active and (time.monotonic() - self.activation_time) < self.duration

    def ignore_collisions(self):
        # 아이템이 활성화되고, 충돌 후 5초 이내에 있는 경우
        return self.active and (time.monotonic() - self.spawn_time) < self.duration

class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.obstacle_width = 24
        self.obstacle_height = 55
        self.car_width = 24
        self.car_height = 55
        self.car_x = width // 2 - self.car_width // 2
        self.car_y = height - self.car_height - 10  # 플레이어 위치
        self.car_speed = 0
        self.car_acceleration = 2  # 가속도
        self.car_max_speed = 15  # 최대 속도
        self.obstacles = []
        self.last_obstacle_time = time.monotonic()
        self.car_image = Image.open('racer/ferrari.png').convert('RGBA').resize((24, 55))
        self.shield_item = ShieldItem(20, 20)  
        self.last_shield_time = time.monotonic()
        self.background_speed = 10  # 배경 스크롤 속도
        self.background_y = 0
        self.background_image = Image.open('racer/circuit.png').resize((width, height)).convert('RGBA')

    def update_background(self):  # 배경 무한 스크롤 반복
        self.background_y += self.background_speed
        if self.background_y > self.height:
            self.background_y = 0 

    def draw_background(self, image):  
        image.paste(self.background_image, (0, self.background_y - self.background_image.height))
        image.paste(self.background_image, (0, self.background_y))

    def spawn_shield(self):  # 일정 간격으로 방어막 생성 
        if time.monotonic() - self.last_shield_time > self.shield_item.spawn_interval:
            self.shield_item.spawn()
            self.last_shield_time = time.monotonic()

    def draw_shield(self, draw):
        if self.shield_item.is_active():
            self.shield_item.draw(draw)

    def spawn_obstacle(self, score):
        if time.monotonic() - self.last_obstacle_time > 2.0: 
            num_obstacles = random.randint(1, 2)  # 범위 내의 개수로 장애물 생성

            for _ in range(num_obstacles):
                if score >= 200:
                    speed_base = 5 + (score // 200) * 2  # 점수 범위마다 기본 속도
                    obstacle_speed = random.uniform(speed_base, speed_base + 3)  # 범위 내의 속도
                else:
                    obstacle_speed = random.uniform(5, 8)

                new_obstacle = Obstacle(self.obstacle_width, self.obstacle_height, obstacle_speed)
                if not any(new_obstacle.collides_with(other) for other in self.obstacles):
                    self.obstacles.append(new_obstacle)

            self.last_obstacle_time = time.monotonic()

    def update(self):
        self.update_background()
        for obstacle in self.obstacles:
            obstacle.update()
            if obstacle.y > self.height:
                self.obstacles.remove(obstacle)
        self.update_car_position()

        self.spawn_shield()
        if self.shield_item.is_active():
            if time.monotonic() - self.shield_item.activation_time > self.shield_item.duration:
                self.shield_item.deactivate()

        self.shield_item.update()
        if self.shield_item.active and self.shield_item.collides_with(self):
            self.shield_item.collect()

        self.spawn_obstacle(score)  

    def use_shield(self):
        if not self.shield_item.is_active() and self.shield_item.count > 0:
            self.shield_item.spawn()
            self.shield_item.count -= 1 

    def check_collision(self):
        for obstacle in self.obstacles:
            if (
                self.car_x < obstacle.x + obstacle.width
                and self.car_x + self.car_width > obstacle.x
                and self.car_y < obstacle.y + obstacle.height
                and self.car_y + self.car_height > obstacle.y
            ):
                if self.shield_item.is_active():  
                    continue
                else:
                    return True
        return False
    
    def draw_text_with_outline(self, draw, text, x, y, font, fill_color, outline_color, outline_width):  # 테두리 텍스트
        for dx, dy in [(dx, dy) for dx in range(-outline_width, outline_width+1) for dy in range(-outline_width, outline_width+1)]:
            draw.text((x+dx, y+dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=fill_color)

    def draw_score_and_shields(self, draw):
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
        score_text = f"Score: {score}"
        shields_text = f"Shields: {self.shield_item.count}"
        text_color = (255, 255, 255)  # 흰색
        outline_color = (0, 0, 0)  # 검정색
        outline_width = 1  # 테두리

        self.draw_text_with_outline(draw, score_text, 10, 10, font, text_color, outline_color, outline_width)
        self.draw_text_with_outline(draw, shields_text, 10, 30, font, text_color, outline_color, outline_width)
        
    def update_car_position(self):
        if not joystick.button_L.value:
            self.car_speed -= self.car_acceleration
        elif not joystick.button_R.value: 
            self.car_speed += self.car_acceleration
        else:
            self.car_speed *= 0.9  # 마찰 효과

        self.car_speed = max(-self.car_max_speed, min(self.car_max_speed, self.car_speed))

        self.car_x += self.car_speed

        self.car_x = max(0, min(self.width - self.car_width, self.car_x))

    def draw_obstacles(self, draw):
        for obstacle in self.obstacles:
            obstacle.draw(draw)

    def draw_car(self, image):
        car_mask = self.car_image.split()[3]
        image.paste(self.car_image, (int(self.car_x), int(self.car_y)), car_mask)


start_screen = Image.open('racer/start.png').convert('RGBA').resize((joystick.disp.width, joystick.disp.height))

game = Game(joystick.disp.width, joystick.disp.height)

joystick.disp.image(start_screen)

# 아무 버튼이나 누를 때까지 대기
while joystick.button_L.value and joystick.button_R.value and joystick.button_A.value and joystick.button_B.value:
    pass


background_image = Image.open('racer/circuit.png').resize((joystick.disp.width, joystick.disp.height)).convert('RGBA')

score = 0

top_scores = []


# 메인 루프
while True:
    command = None
    game.update()

    if not joystick.button_B.value:  # b 버튼으로 방어막 사용
        game.use_shield()

    if game.check_collision():  # 충돌 감지
        print("Game Over! Score:", score)

        top_scores.append(score)
        top_scores.sort(reverse=True)
        top_scores = top_scores[:5]  # 최고 스코어

        game_over_screen = Image.open('racer/gameover.png').convert('RGBA').resize((joystick.disp.width, joystick.disp.height))
        draw = ImageDraw.Draw(game_over_screen)

        text_color = (255, 255, 255)  # 스코어 텍스트
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)

        draw.text((82, 87), "Score: {}".format(score), font=font, fill=text_color)

        for i, top_score in enumerate(top_scores):
            draw.text((95, 107 + i * 15), "{}. {}".format(i + 1, top_score), font=font, fill=text_color)

        joystick.disp.image(game_over_screen)

        while True:
            if not joystick.button_A.value and not joystick.button_B.value:
                continue
            if not joystick.button_A.value:  # a버튼 -> exit 초기 대기 화면으로
                time.sleep(0.1) 

                game = Game(joystick.disp.width, joystick.disp.height)
                score = 0

                start_screen = Image.open('racer/start.png').convert('RGBA').resize((joystick.disp.width, joystick.disp.height))
                joystick.disp.image(start_screen)

                while joystick.button_L.value and joystick.button_R.value and joystick.button_A.value and joystick.button_B.value:
                    pass
                break
            elif not joystick.button_B.value:  # b버튼 -> restart
                time.sleep(0.01)  

                game = Game(joystick.disp.width, joystick.disp.height)
                score = 0

                break

    my_image = background_image.copy()
    draw = ImageDraw.Draw(my_image)

    game.draw_background(my_image) 
    game.draw_shield(my_image)
    game.draw_car(my_image)
    game.draw_obstacles(my_image)
    game.draw_score_and_shields(draw)


    joystick.disp.image(my_image)
    time.sleep(0.001)
    score += 1