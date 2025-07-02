import sensor, image, time, pyb, math

# 初始化摄像头
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.HQVGA)  # 320x240
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.skip_frames(time=2000)

# 加载Haar特征分类器
face_cascade = image.HaarCascade("frontalface", stages=20)
eye_cascade = image.HaarCascade("eye", stages=24)

# 报警系统初始化
buzzer = pyb.Pin("P6", pyb.Pin.OUT_PP)  # 蜂鸣器连接P6
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

# 疲劳检测参数
closed_frames = 0
total_frames = 0
blink_count = 0
last_blink_time = time.ticks_ms()
alarm_active = False

# 阈值设置
EYE_CLOSED_THRESH = 0.3      # PERCLOS阈值
BLINK_RATE_THRESH = 12       # 眨眼频率阈值(次/分钟)
MIN_BLINK_INTERVAL = 300     # 最小眨眼间隔(ms)
ALARM_DURATION = 3000        # 报警持续时间(ms)
ALARM_COOLDOWN = 10000       # 报警冷却时间(ms)
last_alarm_time = 0

clock = time.clock()

def trigger_alarm():
    """触发所有报警装置"""
    global alarm_active, last_alarm_time
    alarm_active = True
    last_alarm_time = time.ticks_ms()

    # 视觉报警（屏幕闪烁红色）
    img.draw_rectangle(0, 0, img.width(), img.height(), color=(255,0,0), fill=True)

    # 声音报警（蜂鸣器）
    for i in range(3):
        buzzer.high()
        pyb.delay(200)
        buzzer.low()
        pyb.delay(200)

    # LED报警
    red_led.on()
    green_led.off()

def stop_alarm():
    """停止所有报警"""
    global alarm_active
    alarm_active = False
    buzzer.low()
    red_led.off()
    green_led.on()


def detect_eyes(img, face):
    """眼睛检测函数"""
    eye_region_top = face[1] + face[3] // 4
    eye_region_height = face[3] // 2
    eye_roi = (face[0], eye_region_top, face[2], eye_region_height)

    eyes = img.find_features(eye_cascade, threshold=0.5, scale_factor=1.1, roi=eye_roi)

    # 绘制检测到的眼睛
    for e in eyes:
        img.draw_rectangle(e, color=(255))

    return eyes

def update_fatigue_status(eyes_detected):
    """更新疲劳状态并返回是否疲劳"""
    global closed_frames, total_frames, blink_count, last_blink_time

    total_frames += 1

    # 眼睛状态检测
    if len(eyes_detected) < 2:  # 眼睛未全部检测到
        closed_frames += 1

        # 检测新的眨眼
        current_time = time.ticks_ms()
        if closed_frames == 1 and time.ticks_diff(current_time, last_blink_time) > MIN_BLINK_INTERVAL:
            blink_count += 1
            last_blink_time = current_time
            blue_led.on()
            pyb.delay(50)
            blue_led.off()
    else:
        closed_frames = 0

    # 计算PERCLOS（眼睛闭合时间比例）
    perclos = closed_frames / 30 if total_frames > 30 else 0

    # 计算眨眼频率
    time_elapsed = time.ticks_diff(time.ticks_ms(), last_blink_time) / 1000  # 秒
    blink_rate = (blink_count / time_elapsed) * 60 if time_elapsed > 0 else 0

    # 判断疲劳状态
    is_fatigued = perclos > EYE_CLOSED_THRESH or (blink_rate < BLINK_RATE_THRESH and blink_count > 3)

    return is_fatigued, perclos, blink_rate

while True:
    clock.tick()
    img = sensor.snapshot()

    # 人脸检测
    faces = img.find_features(face_cascade, threshold=0.5, scale_factor=1.2)

    if faces:
        # 取最大的人脸
        largest_face = max(faces, key=lambda f: f[2]*f[3])
        img.draw_rectangle(largest_face, color=(150))

        # 眼睛检测
        eyes = detect_eyes(img, largest_face)

        # 更新疲劳状态
        fatigued, perclos, blink_rate = update_fatigue_status(eyes)

        # 显示信息
        img.draw_string(10, 10, "Blinks: %d" % blink_count, color=255)
        img.draw_string(10, 25, "Rate: %.1f/min" % blink_rate, color=255)
        img.draw_string(10, 40, "PERCLOS: %.2f" % perclos, color=255)

        if fatigued:
            img.draw_string(10, 55, "FATIGUE WARNING!", color=255, scale=2)

            # 检查是否应该触发报警
            current_time = time.ticks_ms()
            if not alarm_active and time.ticks_diff(current_time, last_alarm_time) > ALARM_COOLDOWN:
                trigger_alarm()
        else:
            img.draw_string(10, 55, "Status: NORMAL", color=255)
            green_led.on()

            # 如果报警激活但不再疲劳，停止报警
            if alarm_active:
                stop_alarm()
    else:
        img.draw_string(10, 10, "No face detected", color=255)
        if alarm_active:
            stop_alarm()

    # 检查报警是否应该自动停止
    if alarm_active and time.ticks_diff(time.ticks_ms(), last_alarm_time) > ALARM_DURATION:
        stop_alarm()

    # 显示帧率
    img.draw_string(10, img.height()-20, "FPS: %.1f" % clock.fps(), color=255)