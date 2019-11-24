#!/usr/bin/env python3
#############################################################################
# Filename    : sevenSegmentDisplay.py
# Description : Ruban de leds adressable commandé par un Raspberry pi
# Author      : papsdroid.fr
# modification: 2019/10/27
########################################################################
import RPi.GPIO as GPIO
import time, threading, os
import board, neopixel

#classe gestion afficheur 7 segments
#------------------------------------------------------------------------------------------------------
class SevenDisplay(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # appel au constructeur de la classe mère Thread
        self.etat = 0                    # 0: non démarré, 1: animation point clignotant 2: animation serpentin, autre: affichage permanent d'un caractère
        self.car = " "                   # caractère à afficher (par défaut éteint)
        self.dec = False                 # point décimal, par défaut non allumé.
        #pin du Raspberry connecté au 74HC595
        self.dataPin   = 17 #pin GPIO17 -> DS Pin14 du 74HC595
        self.latchPin  = 27 #pin GPIO27 -> ST_CP Pin12 du 74HC595
        self.clockPin  = 22 #pin GPIO22 -> CH_CP Pin11 du 74HC595
        #codes hexas correspondants aux lettres 0 à F
        self.dicNum={
            "0": 0xc0, "1": 0xF9, "2": 0xa4,"3": 0xb0, "4": 0x99, "5": 0x92,"6": 0x82,"7": 0xf8,"8": 0x80,"9": 0x90,
            "A": 0x88, "B": 0x83, "C": 0xc6, "D": 0xa1, "E": 0x86,"F": 0x8e, " ": 0xFF #toutes leds éteintes
            }
        #codes binaires correspondants aux segments un par un: pour les animations
        self.dicSegm={
            "A": 0b11111110, "B": 0b11111101, "C": 0b11111011, "D": 0b11110111, "E": 0b11101111, "F": 0b11011111, "G": 0b10111111, "DP":0b01111111, " ": 0b11111111
            }
        self.num = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
        #setup GPIO
        GPIO.setup(self.dataPin, GPIO.OUT)
        GPIO.setup(self.latchPin, GPIO.OUT)
        GPIO.setup(self.clockPin, GPIO.OUT)

        self.start() #démarrage du thread d'affichage

    #exécution du thread
    #-------------------
    def run(self):
        self.etat = 10 # self.etat est mis à jour par l'appui sur le bouton "Selection" ou "Confirmation"
        while (self.etat > 0):
            if self.etat == 1:
                self.animClignoteThread()
            elif self.etat == 2:
                self.animOnThread()
            else:
                self.afficheCarThread()
                time.sleep(0.2) #attente pour ne pas saturer un proc
        self.off() # extinction afficheur si etat=0

    #arrêt du thread
    #---------------
    def stop(self):
        self.etat=0
        
    #éteind l'affichage
    #-----------------
    def off(self):
        self.car = " "
        self.dec = False
        self.afficheCarThread()
    

    #envoie le code binaire val au 74HC595
    #-------------------------------------
    def shiftOut(self,val):
        for i in range(0,8):
            GPIO.output(self.clockPin,GPIO.LOW);
            GPIO.output(self.dataPin,(0x80&(val<<i)==0x80) and GPIO.HIGH or GPIO.LOW)
            GPIO.output(self.clockPin,GPIO.HIGH);

    #affiche le caractère c (0 à F) avec la décimale par défaut non affichée
    #-----------------------------------------------------------------------
    def afficheCarThread(self):
        if self.car.upper() in self.dicNum:
            GPIO.output(self.latchPin,GPIO.LOW)
            val = self.dicNum[self.car.upper()] 
            if self.dec:
                val &= 0x7f
            self.shiftOut(val) #transmet un code hexa au 74HC595 qui correspond à la lettre l
            GPIO.output(self.latchPin,GPIO.HIGH)

    def afficheCar(self, c, dec=False):
        self.car=c
        self.dec=dec
        self.etat=10

    #affiche un seul segment s
    #-------------------------
    def afficheSegmThread(self, s):
        if s.upper() in self.dicSegm:
            GPIO.output(self.latchPin,GPIO.LOW)
            self.shiftOut(self.dicSegm[s.upper()]) #transmet un code hexa au 74HC595 qui correspond à la lettre l
            GPIO.output(self.latchPin,GPIO.HIGH)
        

    #animation point qui clignote
    #----------------------------
    def animClignoteThread(self):
        self.afficheSegmThread("DP")
        time.sleep(0.2)
        self.afficheSegmThread(" ")
        time.sleep(0.2)

    def animClignote(self):
        self.etat=1


    #animation de démarrage: serpentin qui parcourt un 8
    #---------------------------------------------------        
    def animOnThread(self):
        seqSegm = ["A", "B", "G", "E", "D", "C", "G", "F"]
        for i in range(len(seqSegm)):
            self.afficheSegmThread(seqSegm[i])
            time.sleep(0.1)

    def animOn(self):
        self.etat=2;    

#classe animation du rubans de leds
#------------------------------------------------------------------------------------------------------
class RubanLeds(threading.Thread):
    def __init__(self, nb_leds):
        threading.Thread.__init__(self)  # appel au constructeur de la classe mère Thread
        self.pixel_pin = board.D18       # GPIO18 envoie les commandes au ruban
        self.nb_leds = nb_leds           #nb de leds
        self.pixels = neopixel.NeoPixel(self.pixel_pin, self.nb_leds, brightness=0.2, auto_write=False, pixel_order=neopixel.GRB)
        self.etat=False
        self.id_animation=0
        self.start() #démarrage du thread d'animaton des leds
        self.color_bMuse = 0x1311f0  #bleu Muse
        self.color_rMuse = 0xcd00c4  #rose Muse
        self.index=0 #pour alternance de couleurs

    #exécution du thread
    #-------------------
    def run(self):
        self.etat = True
        while (self.etat):
            if self.id_animation>0:
                exec("self.anim_" + str(self.id_animation) + "()") # exécute la méthode self.anim_n() , n= n° d'animation > 0
            else:
                self.off()
                time.sleep(0.1)   
        self.off() # extinction afficheur si etat=0

    #arrêt du thread
    #---------------
    def stop(self):
        self.etat=False
        
    #extinction des leds
    #------------------------------
    def off(self):
        self.pixels.fill((0, 0, 0))
        self.pixels.show()


    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    # ----------------------------------------------------
    def wheel(self, pos):
        if pos < 0 or pos > 255:
            r = g = b = 0
        elif pos < 85:
            r = int(pos * 3)
            g = int(255 - pos*3)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int(255 - pos*3)
            g = 0
            b = int(pos*3)
        else:
            pos -= 170
            r = 0
            g = int(pos*3)
            b = int(255 - pos*3)
        return (r, g, b)

    #cycle de couleurs arc en ciel
    #-----------------------------
    def rainbow_cycle(self):
        for j in range(255):
            for i in range(self.nb_leds):
                pixel_index = (i * 256 // self.nb_leds) + j
                self.pixels[i] = self.wheel(pixel_index & 255)
            self.pixels.show()
            time.sleep(0.001)

    #poursuite de n leds de couleur c, sur fond de couleur c_fond, délais en secondes
    #---------------------------------------------------------------------------------
    def poursuite(self, c_fond, c, n, delais):
        self.pixels.fill(c_fond)
        for i in range(self.nb_leds + n):
            if i-n>=0:
                self.pixels[i-n] = c_fond
            if i<self.nb_leds:
                self.pixels[i] = c
            self.pixels.show()
            time.sleep(delais)

    #poursuite arc-en-ciel
    #---------------------
    def poursuite_rainbow(self, delais):
        self.pixels.fill(0)
        for i in range(self.nb_leds+1):
            if i>0:
                self.pixels[i-1] = 0
            if i<self.nb_leds:
                self.pixels[i] = self.wheel((i*256//self.nb_leds) & 255)
            self.pixels.show()
            time.sleep(delais)

        
    #n leds sucessives en alternance de couleur c1 et C2), délais en secondes
    #------------------------------------------------------------------------
    def alterne(self, c1, c2, n, delais):
        cc1, cc2 = c1, c2
        for k in range(2):
            rang=0
            for i in range(int(self.nb_leds / (2*n))):
                for j in range(n):
                    self.pixels[rang] = cc1
                    rang+=1
                for j in range(n):
                    self.pixels[rang] = cc2
                    rang+=1
            self.pixels.show()
            time.sleep(delais)
            #echange couleurs cc1 et cc2
            cctmp=cc1
            cc1=cc2
            cc2=cctmp

    #fermeture couleur c sur fond c_fond, délais en secondes
    def fermeture(self, c_fond, c, delais):
        self.pixels.fill(c_fond)
        self.pixels.show()
        time.sleep(delais)
        rang=0
        for i in range(int(self.nb_leds/2)):
            self.pixels[rang] = c
            self.pixels[self.nb_leds-1-rang] = c
            rang+=1
            self.pixels.show()
            time.sleep(delais)

    #stroboscope alternance 2 couleurs
    #---------------------------------
    def strob(self, c1, c2, delais):
        self.pixels.fill(c1)
        self.pixels.show()
        time.sleep(delais)
        self.pixels.fill(0)
        self.pixels.show()
        time.sleep(delais)
        self.pixels.fill(c2)
        self.pixels.show()
        time.sleep(delais)

    #stroboscope effet arc-en-ciel
    #-----------------------------
    def strob_rainbow(self, delais):
        self.pixels.fill(self.wheel((self.index*256//self.nb_leds) & 255))
        self.pixels.show()
        time.sleep(delais)
        self.pixels.fill(0)
        self.pixels.show()
        time.sleep(delais)
        self.index +=1
        if self.index == self.nb_leds:
            self.index=0
        
    #animations du ruban de leds
    #---------------------------
       
    # mode démo
    def anim_1(self):
        self.fermeture(self.color_bMuse, self.color_rMuse, 0.04)
        self.rainbow_cycle()
        self.poursuite_rainbow(0.01)
        
    # arc-en-ciel
    def anim_2(self):
        self.rainbow_cycle()

    # poursuite 1 led rouge sur fond noir
    def anim_3(self):
        self.poursuite(0, 0xff0000, 1, 0.01)

    # poursuite arc-en-ciel
    def anim_4(self):
        self.poursuite_rainbow(0.01)

    # poursuite 3 couleur_rMuse sur fond couleur_bMuse
    def anim_5(self):
        self.poursuite(self.color_bMuse, self.color_rMuse, 3, 0.02)

    # alternance n leds sucessives 2 couleurs
    def anim_6(self):
        self.alterne(self.color_bMuse, self.color_rMuse, 3, 0.3)
        
    # fermeture couleur c sur fond c_fond
    def anim_7(self):
        self.fermeture(self.color_bMuse, self.color_rMuse, 0.04)

    #stroboscope 2 couleurs
    def anim_8(self):
        self.strob(self.color_bMuse, self.color_rMuse, 0.08)

    #stroboscope arc-en-ciel
    def anim_9(self):
        self.strob_rainbow(0.08)

        

#classe d'Application principale
#------------------------------------------------------------------------------------------------------
class Application:
    def __init__(self):
        print("démarrage LedDroid")
        #GPIO.setmode(GPIO.BOARD)      # identification des GPIOs par location physique
        self.display = SevenDisplay()  # affichage 7 segments
        self.leds = RubanLeds(30)     # rubans de 30 leds
        self.buttonConfirmPin = 21     # bouton de confirmation arrêt/relance d'une animation
        self.buttonSelectPin = 20      # bouton pour changement d'animation
        self.buttonOffPin = 16         # bouton d'extinction
        #pin associés aux boutons poussoirs
        GPIO.setup(self.buttonSelectPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)     # mode INPUT, pull_up=high
        GPIO.setup(self.buttonConfirmPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # mode INPUT, pull_up=high
        GPIO.setup(self.buttonOffPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)        # mode INPUT, pull_up=high
        GPIO.add_event_detect(self.buttonSelectPin,GPIO.FALLING,callback = self.buttonSelectEvent, bouncetime=300)
        GPIO.add_event_detect(self.buttonConfirmPin,GPIO.FALLING,callback = self.buttonConfirmEvent, bouncetime=300)
        GPIO.add_event_detect(self.buttonOffPin,GPIO.FALLING,callback=self.buttonOffEvent, bouncetime=300)
        self.seqIdMin=1          # seqIdMin 1 à 15 (0xF)
        self.seqIdMax=9          # seqIdMax 1 à 15 (0xF)
        self.seqId=self.seqIdMin # id de la séquence à jouer, dans l'intervalle [seqIdMin, seIdMan]
        self.confirm = False     #si True: la séquence seqId est confirmée
        self.display.afficheCar(self.display.num[self.seqId])    

    #fonction exécutée quand le bouton poussoir "OFF" est pressé
    #-----------------------------------------------------------
    def buttonOffEvent(self,channel):
        print('Extinction Raspberry...')
        self.display.stop() # arret du thread d'affichage
        self.leds.stop()    # arrêt du thread d'animation rubans de leds
        time.sleep(1)
        os.system('sudo halt')
    
    #fonction exécutée quand le bouton poussoir "select" est pressé
    # incrémente seqId et met à jour l'affichage
    #---------------------------------------------------------------
    def buttonSelectEvent(self, channel):
        if not(self.confirm):
            self.seqId += 1
            if self.seqId > self.seqIdMax:
                self.seqId = self.seqIdMin
            self.display.afficheCar(self.display.num[self.seqId])

    #fonction exécutée quand le bouton poussoir "confirm" est pressé
    # lance ou arrête l'animation en cours
    #---------------------------------------------------------------
    def buttonConfirmEvent(self, channel):
        if self.confirm:
            #arrête l'animation leds en cours
            self.display.afficheCar(self.display.num[self.seqId])
            self.leds.id_animation=0
            self.confirm=False
        else:
            #démarre l'animation de leds
            #print('animation leds num', self.seqId)
            self.display.animOn()
            self.leds.id_animation = self.seqId
            self.confirm=True

    #méthode de destruction    
    def destroy(self):
        print ('bye')
        self.display.stop() # arret du thread d'affichage
        self.leds.stop()    # arrêt du thread d'animation rubans de leds
        time.sleep(1)
        GPIO.cleanup()

    #boucle principale du prg
    def loop(self):
        while True:
            if self.confirm:
                self.display.animOn()
            time.sleep(0.1)
            
if __name__ == '__main__':
    appl=Application() 
    try:
        appl.loop()
    except KeyboardInterrupt:  # interruption clavier CTRL-C: appel à la méthode destroy() de appl.
        appl.destroy()
