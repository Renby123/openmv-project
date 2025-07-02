import sensor, ml, uos, gc,time
from machine  import UART

uart = UART(3,9600)  #3号串口
uart.init(9600, bits=8, parity=None, stop=1) #波特率为 9600，无校验位，数据位为 8，停止位为 1

sensor.reset() #重置传感器
sensor.set_pixformat(sensor.GRAYSCALE)#设置图像的像素格式为灰度图
sensor.set_framesize(sensor.QQVGA)#设置图像的分辨率为 QQVGA（160x120）
sensor.skip_frames(time=2000)#初始化摄像头后，跳过一段时间（2秒）让传感器稳定
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

net = None
labels = None

try:
    net = ml.Model("trained.tflite", load_to_fb=uos.stat('trained.tflite')[6] > (gc.mem_free() - (64*1024)))
except Exception as e:
    print(e)
    raise Exception('Failed to load "trained.tflite", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')

try:
    labels = [line.rstrip('\n') for line in open("labels.txt")]
except Exception as e:
    raise Exception('Failed to load "labels.txt", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')

threshold = [(250, 255)]

while(1):
    txt=""
    img = sensor.snapshot()
    img.lens_corr(1.5)
    img2 = img.copy().binary([(0, 60)])
    blobss = img2.find_blobs(threshold,area_threshold=100,margin=100)
    blobs = sorted(blobss, key=lambda blob: blob.x())
    for b in blobs:
        if 10<b.x()<150 and 10<b.y()<110:
            roi=(b.x()-5,b.y()-5,b.w()+10,b.h()+10)
            img.draw_rectangle((b.x()-5,b.y()-5,b.w()+10,b.h()+10))
            cropped_img = img2.copy(x_scale=96/(b.w()+10),y_scale=96/(b.h()+10),roi=roi)
            predictions_list = list(zip(labels, net.predict([cropped_img])[0].flatten().tolist()))
            if predictions_list:
                predictions_list = sorted(predictions_list,key=lambda x:x[1],reverse=True)
                number = predictions_list[0][0]
                txt+=number
    if txt:
        num=int(txt)
        if num<256:
            print(num)
            #uart.write(bytearray([num]))