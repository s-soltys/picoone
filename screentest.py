from machine import Pin
import time
import random
import _thread
from lcd import LCD_0inch96, RED, GREEN, BLUE, WHITE, BLACK, DKRED, PINK, DKGRN

    
def run():
    # start LED blinking in background
    led = Pin("LED", Pin.OUT)
    blink_running = True
    def blink_loop():
        delay = 0.2
        while blink_running:
            for second in range(1, 11):
                for _ in range(second):
                    if not blink_running:
                        break
                    led.on()
                    time.sleep(delay)
                    led.off()
                    time.sleep(delay)
                    delay += random.uniform(-0.04, 0.04)
                    delay = max(0.01, min(0.5, delay))
                if not blink_running:
                    break
                time.sleep(0.5)
    _thread.start_new_thread(blink_loop, ())

    lcd = LCD_0inch96()   
    lcd.fill(BLACK)   
    lcd.text("Hello Kim!",15,15,RED)
    lcd.text("Can't wait",15,35,WHITE)    
    lcd.text("to see you :*",15,55,WHITE)
    lcd.display()
    
    # rose top right
    cx = 140
    # petals (overlapping ellipses)
    lcd.ellipse(cx, 18, 7, 9, RED, True)
    lcd.ellipse(cx-6, 20, 6, 7, RED, True)
    lcd.ellipse(cx+6, 20, 6, 7, RED, True)
    lcd.ellipse(cx-3, 14, 5, 6, PINK, True)
    lcd.ellipse(cx+3, 14, 5, 6, PINK, True)
    lcd.ellipse(cx, 20, 4, 5, DKRED, True)
    # spiral centre
    lcd.ellipse(cx, 17, 2, 3, DKRED, True)
    # stem
    lcd.vline(cx, 28, 22, DKGRN)
    lcd.vline(cx-1, 28, 22, DKGRN)
    # leaves
    lcd.ellipse(cx+5, 40, 5, 3, DKGRN, True)
    lcd.ellipse(cx-6, 46, 5, 3, DKGRN, True)

    lcd.hline(0,0,160,BLUE)
    lcd.hline(0,79,160,BLUE)
    lcd.vline(0,0,80,BLUE)
    lcd.vline(159,0,80,BLUE) 
    
    lcd.display()

    KEY_UP = Pin(2,Pin.IN,Pin.PULL_UP)
    KEY_DOWN = Pin(18,Pin.IN,Pin.PULL_UP)
    KEY_LEFT= Pin(16,Pin.IN,Pin.PULL_UP)
    KEY_RIGHT= Pin(20,Pin.IN,Pin.PULL_UP)
    KEY_CTRL=Pin(3,Pin.IN,Pin.PULL_UP)
    KEY_A=Pin(15,Pin.IN,Pin.PULL_UP)
    KEY_B=Pin(17,Pin.IN,Pin.PULL_UP)

    # wait for any button press
    while KEY_UP.value() and KEY_DOWN.value() and KEY_LEFT.value() and KEY_RIGHT.value() and KEY_CTRL.value() and KEY_A.value() and KEY_B.value():
        time.sleep(0.05)
    # debounce
    time.sleep(0.2)

    #game GUI
###    
    lcd.fill(BLACK)
    
    # fill each cell with a random color
    for row in range(8):
        for col in range(16):
            c = random.getrandbits(16)
            lcd.fill_rect(col*10+1, row*10+1, 9, 9, c)
    
    i=0
    while(i<=80):    
        lcd.hline(0,i,160,BLACK)
        i=i+10  
    i=0
    while(i<=160):
        lcd.vline(i,0,80,BLACK)
        i=i+10 
    lcd.display()
### 
    
    x=80
    y=40
    color=RED
    colorflag=0
        
    while(1):
        key_flag=1
        if(key_flag and (KEY_UP.value()==0 or KEY_DOWN.value()==0 \
        or KEY_LEFT.value()==0 or KEY_RIGHT.value()==0 \
        or KEY_CTRL.value()==0 or KEY_A.value()==0 \
        or KEY_B.value()==0 )):
            time.sleep(0.05)
            key_flag=0
            m=x
            n=y
            ###go up
            if(KEY_UP.value() == 0):
                y=y-10
                if(y<0):
                    y=70
            if(KEY_DOWN.value() == 0):
                y=y+10
                if(y>=80):
                    y=0
            if(KEY_LEFT.value() == 0):
                x=x-10
                if(x<0):
                    x=150
            if(KEY_RIGHT.value() == 0):
                x=x+10 
                if(x>=160):
                    x=0
            if(KEY_CTRL.value() == 0): 
                colorflag+=1
                if(colorflag==1):
                    color=RED
                elif(colorflag==2):
                    color=GREEN                
                elif(colorflag==3):
                    color=BLUE
                    colorflag=0
                
            lcd.fill_rect(m,n,10,10,WHITE)
            lcd.hline(m,n,10,BLACK)
            lcd.hline(m,n+10,10,BLACK)
            lcd.vline(m,n,10,BLACK)
            lcd.vline(m+10,n,10,BLACK)
            
   
            lcd.rect(x+1,y+1,9,9,color)
            
            if(KEY_A.value() == 0):
                lcd.fill_rect(x+1,y+1,9,9,color)
                lcd.fill_rect(m+1,n+1,9,9,color)

            if(KEY_B.value() == 0):
                lcd.fill(WHITE)                    
                i=0
                while(i<=80):    
                    lcd.hline(0,i,160,BLACK)
                    i=i+10  
                i=0
                while(i<=160):
                    lcd.vline(i,0,80,BLACK)
                    i=i+10    
            

                
        lcd.display()   
    
    time.sleep(1)

if __name__=='__main__':
    run()
