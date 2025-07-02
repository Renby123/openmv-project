THRESHOLD = (0, 40)

import sensor, image, time, math
from pyb import UART

sensor.reset()#重置摄像头
sensor.set_pixformat(sensor.GRAYSCALE)#设置像素格式为灰度
sensor.set_framesize(sensor.QQVGA)#设置帧大小为QQVGA
sensor.skip_frames(time = 2000)#过初始2s以稳定图像
clock = time.clock()#设置时钟
uart = UART(3,115200)
uart.init(115200, bits=8, parity=None, stop=1)

def degree(line):
    if line[6]>90:
        return line[6]-90
    elif line[6]<90:
        return line[6]+90

while(True):
    clock.tick()
    img = sensor.snapshot().binary([THRESHOLD])
    img.lens_corr(1.5)
    left_line = img.get_regression([(255,255)],roi=(0,0,80,60))
    right_line = img.get_regression([(255,255)],roi=(80,0,80,60))
    main_degree = math.pi/2
    if left_line and right_line:
        main_degree = (degree(left_line)+degree(right_line))/2
    elif left_line:
        main_degree = degree(left_line)
    elif right_line:
        main_degree = degree(right_line)
    uart.write(bytearray([round(main_degree)]))
    main_degree = math.pi*(main_degree)/180
    d_y=round(20*math.sin(main_degree))
    d_x=round(20*math.cos(main_degree))
    img.draw_line(80,50,80-d_x,50-d_y)