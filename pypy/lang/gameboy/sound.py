"""
PyGirl Emulator
 
Audio Processor Unit (Sharp LR35902 APU)
"""

from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import iMemory

class Channel(object):

    audio_index = 0
    audio_length = 0
    audio_frequency = 0
    
    def __init__(self, sample_rate, frequency_table):
        self.sample_rate     = int(sample_rate)
        self.frequency_table = frequency_table
        self.audio_length    = 0
        self.audio_envelope  = 0
        self.audio_frequency = 0
        self.audio_playback  = 0
        self.nr0             = 0
        self.nr1             = 0
        self.nr2             = 0
        self.nr4             = 0
        self.nr3             = 0
        self.audio_index     = 0
        self.audio_length    = 0
        self.audio_frequency = 0
        self.enabled         = False
        #XXX need to push this up into the Sound class
        self.output_enable  = False
        
    def reset(self):
        self.audio_index = 0
    
    def get_audio_length(self):
        return self.audio_length

    def get_audio_envelope(self):
        return self.audio_envelope

    def get_audio_frequency(self):
        return self.audio_frequency

    def get_audio_playback(self):
        return self.audio_playback
        

    
# ------------------------------------------------------------------------------

#SquareWaveGenerator
class Channel1(Channel):
        # Audio Channel 1 int
    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
        self.sample_sweep            = 0
        self.audio_1_index           = 0
        self.audio_1_length          = 0
        self.audio_volume            = 0
        self.audio_1_envelope_length = 0
        self.sample_sweep_length     = 0
        self.audio_1_frequency       = 0
    
     # Audio Channel 1
    def get_audio_sweep(self):
        return self.sample_sweep

    def set_audio_sweep(self, data):
        self.sample_sweep        = data
        self.sample_sweep_length = (constants.SOUND_CLOCK / 128) * \
                                ((self.sample_sweep >> 4) & 0x07)

    def set_audio_length(self, data):
        self.audio_length   = data
        self.audio_1_length = (constants.SOUND_CLOCK / 256) * \
                            (64 - (self.audio_length & 0x3F))

    def set_audio_envelope(self, data):
        self.audio_envelope = data
        if (self.audio_playback & 0x40) != 0:
            return
        if (self.audio_envelope >> 4) == 0:
            self.audio_volume = 0
        elif self.audio_1_envelope_length == 0 and \
             (self.audio_envelope & 0x07) == 0:
            self.audio_volume = (self.audio_volume + 1) & 0x0F
        else:
            self.audio_volume = (self.audio_volume + 2) & 0x0F

    def set_audio_frequency(self, data):
        self.audio_frequency = data
        index = self.audio_frequency + ((self.audio_playback & 0x07) << 8)
        self.audio_1_frequency = self.frequency_table[index]

    def set_audio_playback(self, data):
        self.audio_playback = data
        self.audio_1_frequency = self.frequency_table[self.audio_frequency
                + ((self.audio_playback & 0x07) << 8)]
        if (self.audio_playback & 0x80) != 0:
            self.enabled = True
            if (self.audio_playback & 0x40) != 0 and self.audio_1_length == 0:
                self.audio_1_length = (constants.SOUND_CLOCK / 256) * \
                                    (64 - (self.audio_length & 0x3F))
            self.sample_sweep_length = (constants.SOUND_CLOCK / 128) * \
                                    ((self.sample_sweep >> 4) & 0x07)
            self.audio_volume = self.audio_envelope >> 4
            self.audio_1_envelope_length = (constants.SOUND_CLOCK / 64) * \
                                        (self.audio_envelope & 0x07)

    def update_audio(self):
        self.update_enable()
        self.update_volume_and_envelope()
        self.update_frequency_and_playback()

    def update_enable(self):
        if (self.audio_playback & 0x40) != 0 and self.audio_1_length > 0:
            self.audio_1_length-=1
            if self.audio_1_length <= 0:
                self.enabled = False
    
    def update_volume_and_envelope(self):
        if self.audio_1_envelope_length <= 0:
            return
        self.audio_1_envelope_length -= 1
        if self.audio_1_envelope_length <= 0:
            if (self.audio_envelope & 0x08) != 0:
                if (self.audio_volume < 15):
                    self.audio_volume += 1
            elif self.audio_volume > 0:
                self.audio_volume -= 1
            self.audio_1_envelope_length += (constants.SOUND_CLOCK / 64) * \
                                         (self.audio_envelope & 0x07)
                                             
    def update_frequency_and_playback(self):
        if self.sample_sweep_length <= 0:
            return
        self.sample_sweep_length-=1
        if self.sample_sweep_length > 0:
            return
        sweep_steps = (self.sample_sweep & 0x07)
        if sweep_steps != 0:
            frequency = ((self.audio_playback & 0x07) << 8) + \
                        self.audio_frequency
            if (self.sample_sweep & 0x08) != 0:
                frequency -= frequency >> sweep_steps
            else:
                frequency += frequency >> sweep_steps
            if frequency < 2048:
                self.audio_1_frequency = self.frequency_table[frequency]
                self.audio_frequency = frequency & 0xFF
                self.audio_playback = (self.audio_playback & 0xF8) + \
                                     ((frequency >> 8) & 0x07)
            else:
                self.audio_1_frequency = 0
                self.output_enable &= ~0x01
        self.sample_sweep_length += (constants.SOUND_CLOCK / 128) * \
                                 ((self.sample_sweep >> 4) & 0x07)
                                         
    def mix_audio(self, buffer, length, output_terminal):
        wave_pattern = self.get_current_wave_pattern()
        for index in range(0, length, 3):
            self.audio_1_index += self.audio_1_frequency
            if (self.audio_1_index & (0x1F << 22)) >= wave_pattern:
                if (output_terminal & 0x10) != 0:
                    buffer[index + 0] -= self.audio_volume
                if (output_terminal & 0x01) != 0:
                    buffer[index + 1] -= self.audio_volume
            else:
                if (output_terminal & 0x10) != 0:
                    buffer[index + 0] += self.audio_volume
                if (output_terminal & 0x01) != 0:
                    buffer[index + 1] += self.audio_volume
                    
    def get_current_wave_pattern(self):
        wave_pattern = 0x18
        if (self.audio_length & 0xC0) == 0x00:
            wave_pattern = 0x04
        elif (self.audio_length & 0xC0) == 0x40:
            wave_pattern = 0x08
        elif (self.audio_length & 0xC0) == 0x80:
            wave_pattern = 0x10
        return wave_pattern << 22
        
                    
    

#SquareWaveGenerator
class Channel2(Channel):

    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
        self.audio_2_index           = 0
        self.audio_2_length          = 0
        self.audio_volume            = 0
        self.audio_2_envelope_length = 0
        self.audio_2_frequency       = 0
      
    # Audio Channel 2
    def set_audio_length(self, data):
        self.audio_length = data
        self.audio_2_length = (constants.SOUND_CLOCK / 256) * \
                            (64 - (self.audio_length & 0x3F))

    def set_audio_envelope(self, data):
        self.audio_envelope = data
        if (self.audio_playback & 0x40) == 0:
            if (self.audio_envelope >> 4) == 0:
                self.audio_volume = 0
            elif self.audio_2_envelope_length == 0 and \
                 (self.audio_envelope & 0x07) == 0:
                self.audio_volume = (self.audio_volume + 1) & 0x0F
            else:
                self.audio_volume = (self.audio_volume + 2) & 0x0F

    def set_audio_frequency(self, data):
        self.audio_frequency   = data
        self.audio_2_frequency = self.frequency_table[self.audio_frequency\
                                    + ((self.audio_playback & 0x07) << 8)]

    def set_audio_playback(self, data):
        self.audio_playback    = data
        self.audio_2_frequency = self.frequency_table[self.audio_frequency\
                                    + ((self.audio_playback & 0x07) << 8)]
        if (self.audio_playback & 0x80) != 0:
            self.enabled = True
            if (self.audio_playback & 0x40) != 0 and self.audio_2_length == 0:
                self.audio_2_length = (constants.SOUND_CLOCK / 256) * \
                                    (64 - (self.audio_length & 0x3F))
            self.audio_volume = self.audio_envelope >> 4
            self.audio_2_envelope_length = (constants.SOUND_CLOCK / 64) * \
                                        (self.audio_envelope & 0x07)
    
    def update_audio(self):
        self.update_enable()
        self.update_volume_and_envelope()
        
    def update_enable(self):
        if (self.audio_playback & 0x40) != 0 and self.audio_2_length > 0:
            self.audio_2_length-=1
            if self.audio_2_length <= 0:
                self.enabled = False
    
    def update_volume_and_envelope(self):
        if self.audio_2_envelope_length <= 0:
            return
        self.audio_2_envelope_length-=1
        if self.audio_2_envelope_length > 0:
            return
        if (self.audio_envelope & 0x08) != 0:
            if self.audio_volume < 15:
                self.audio_volume+=1
        elif self.audio_volume > 0:
            self.audio_volume-=1
        self.audio_2_envelope_length += (constants.SOUND_CLOCK / 64) *\
                                     (self.audio_envelope & 0x07)
        
    def mix_audio(self, buffer, length, output_terminal):
        wave_pattern = self.get_current_wave_pattern()
        for index in range(0, length):
            self.audio_2_index += self.audio_2_frequency
            if (self.audio_2_index & (0x1F << 22)) >= wave_pattern:
                if (output_terminal & 0x20) != 0:
                    buffer[index + 0] -= self.audio_volume
                if (output_terminal & 0x02) != 0:
                    buffer[index + 1] -= self.audio_volume
            else:
                if (output_terminal & 0x20) != 0:
                    buffer[index + 0] += self.audio_volume
                if (output_terminal & 0x02) != 0:
                    buffer[index + 1] += self.audio_volume

    def get_current_wave_pattern(self):
        wave_pattern = 0x18
        if (self.audio_length & 0xC0) == 0x00:
            wave_pattern = 0x04
        elif (self.audio_length & 0xC0) == 0x40:
            wave_pattern = 0x08
        elif (self.audio_length & 0xC0) == 0x80:
            wave_pattern = 0x10
        return wave_pattern << 22

    
    
#SquareWaveGenerator
class Channel3(Channel):  

    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
        self.audio_enable       = 0
        self.audio_level        = 0
        self.audio_3_index      = 0
        self.audio_3_length     = 0
        self.audio_3_frequency  = 0
        self.audio_wave_pattern = [0]*16
    
    def get_audio_enable(self):
        return self.audio_enable

    def get_audio_level(self):
        return self.audio_level
    
    #FIXME strange number here
    def get_audio_4_frequency(self):
        return self.audio_frequency

    def set_audio_enable(self, data):
        self.audio_enable = data & 0x80
        if (self.audio_enable & 0x80) == 0:
            self.enabled = False

    def set_audio_length(self, data):
        self.audio_length = data
        self.audio_3_length = (constants.SOUND_CLOCK / 256) * \
                            (256 - self.audio_length)

    def set_audio_level(self, data):
        self.audio_level = data

    def set_audio_frequency(self, data):
        self.audio_frequency = data
        index = ((self.audio_playback & 0x07) << 8) + self.audio_frequency
        self.audio_3_frequency = self.frequency_table[index] >> 1

    def set_audio_playback(self, data):
        self.audio_playback = data
        index = ((self.audio_playback & 0x07) << 8) + self.audio_frequency
        self.audio_3_frequency = self.frequency_table[index] >> 1
        if (self.audio_playback & 0x80) != 0 and (self.audio_enable & 0x80) != 0:
            self.enabled = True
            if (self.audio_playback & 0x40) != 0 and self.audio_3_length == 0:
                self.audio_3_length = (constants.SOUND_CLOCK / 256) *\
                                    (256 - self.audio_length)
    
    def set_audio_wave_pattern(self, address, data):
        self.audio_wave_pattern[address & 0x0F] = data

    def get_audio_wave_pattern(self, address):
        return self.audio_wave_pattern[address & 0x0F] & 0xFF

    def update_audio(self):
        if (self.audio_playback & 0x40) != 0 and self.audio_3_length > 0:
            self.audio_3_length-=1
            if self.audio_3_length <= 0:
                self.output_enable &= ~0x04

    def mix_audio(self, buffer, length, output_terminal):
        wave_pattern = self.get_current_wave_pattern()
        for index in range(0, length, 2):
            self.audio_3_index += self.audio_3_frequency
            sample = self.audio_wave_pattern[(self.audio_3_index >> 23) & 0x0F]
            if ((self.audio_3_index & (1 << 22)) != 0):
                sample = (sample >> 0) & 0x0F
            else:
                sample = (sample >> 4) & 0x0F
            sample = int(((sample - 8) << 1) >> self.audio_level)
            if (output_terminal & 0x40) != 0:
                buffer[index + 0] += sample
            if (output_terminal & 0x04) != 0:
                buffer[index + 1] += sample
    
    def get_current_wave_pattern(self):
        wave_pattern = 2
        if (self.audio_level & 0x60) == 0x00:
            wave_pattern = 8
        elif (self.audio_level & 0x60) == 0x40:
            wave_pattern = 0
        elif (self.audio_level & 0x60) == 0x80:
            wave_pattern = 1
        return wave_pattern
            
    
class NoiseGenerator(Channel):
        
    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
            # Audio Channel 4 int
        self.audio_length            = 0
        self.audio_polynomial        = 0
        self.audio_4_index           = 0
        self.audio_4_length          = 0
        self.audio_volume            = 0
        self.audio_4_envelope_length = 0
        self.audio_4_frequency       = 0
        self.generate_noise_frequency_ratio_table()
        self.generate_noise_tables()
    
    def generate_noise_frequency_ratio_table(self):
         # Polynomial Noise Frequency Ratios
         # 4194304 Hz * 1 / 2^3 * 2 4194304 Hz * 1 / 2^3 * 1 4194304 Hz * 1 / 2^3 *
         # 1 / 2 4194304 Hz * 1 / 2^3 * 1 / 3 4194304 Hz * 1 / 2^3 * 1 / 4 4194304 Hz *
         # 1 / 2^3 * 1 / 5 4194304 Hz * 1 / 2^3 * 1 / 6 4194304 Hz * 1 / 2^3 * 1 / 7
        self.noiseFreqRatioTable = [0] * 8
        sampleFactor = ((1 << 16) / self.sample_rate)
        for ratio in range(0, 8):
            divider = 1
            if ratio != 0:
                divider = 2 * ratio
            self.noiseFreqRatioTable[ratio] = (constants.GAMEBOY_CLOCK / \
                                             divider) *sampleFactor

    def generate_noise_tables(self):
        self.create_7_step_noise_table()
        self.create_15_step_noise_table()
        
    def create_7_step_noise_table(self):
         # Noise Tables
        self. noise_step_7_table = [0]*4
        polynomial = 0x7F
        #  7 steps
        for  index in range(0, 0x7F):
            polynomial = (((polynomial << 6) ^ (polynomial << 5)) & 0x40) | \
                         (polynomial >> 1)
            if (index & 31) == 0:
                self.noise_step_7_table[index >> 5] = 0
            self.noise_step_7_table[index >> 5] |= (polynomial & 1) << \
                                                (index & 31)
            
    def create_15_step_noise_table(self):
        #  15 steps&
        self.noise_step_15_table = [0]*1024
        polynomial = 0x7FFF
        for index in range(0, 0x7FFF):
            polynomial = (((polynomial << 14) ^ (polynomial << 13)) & \
                         0x4000) | (polynomial >> 1)
            if (index & 31) == 0:
                self.noise_step_15_table[index >> 5] = 0
            self.noise_step_15_table[index >> 5] |= (polynomial & 1) << \
                                                 (index & 31)
    
     # Audio Channel 4
    def get_audio_length(self):
        return self.audio_length

    def get_audio_polynomial(self):
        return self.audio_polynomial

    def get_audio_playback(self):
        return self.audio_playback

    def set_audio_length(self, data):
        self.audio_length = data
        self.audio_4_length = (constants.SOUND_CLOCK / 256) * \
                            (64 - (self.audio_length & 0x3F))

    def set_audio_envelope(self, data):
        self.audio_envelope = data
        if (self.audio_playback & 0x40) is not 0:
            return
        if (self.audio_envelope >> 4) == 0:
            self.audio_volume = 0
        elif self.audio_4_envelope_length == 0 and \
             (self.audio_envelope & 0x07) == 0:
            self.audio_volume = (self.audio_volume + 1) & 0x0F
        else:
            self.audio_volume = (self.audio_volume + 2) & 0x0F

    def set_audio_polynomial(self, data):
        self.audio_polynomial = data
        if (self.audio_polynomial >> 4) <= 12:
            freq = self.noiseFreqRatioTable[self.audio_polynomial & 0x07]
            self.audio_4_frequency = freq >> ((self.audio_polynomial >> 4) + 1)
        else:
            self.audio_4_frequency = 0

    def set_audio_playback(self, data):
        self.audio_playback = data
        if (self.audio_playback & 0x80) == 0:
            return
        self.enabled = True
        if (self.audio_playback & 0x40) != 0 and self.audio_4_length == 0:
            self.audio_4_length = (constants.SOUND_CLOCK / 256) * \
                                (64 - (self.audio_length & 0x3F))
        self.audio_volume = self.audio_envelope >> 4
        self.audio_4_envelope_length = (constants.SOUND_CLOCK / 64) * \
                                    (self.audio_envelope & 0x07)
        self.audio_4_index = 0

    def update_audio(self):
        self.update_enabled()
        self.update_envelope_and_volume()
    
    def update_enabled(self):
        if (self.audio_playback & 0x40) != 0 and self.audio_4_length > 0:
            self.audio_4_length-=1
            if self.audio_4_length <= 0:
                self.output_enable &= ~0x08
        
    def update_envelope_and_volume(self):
        if self.audio_4_envelope_length <= 0:
            return
        self.audio_4_envelope_length-=1
        if self.audio_4_envelope_length > 0:
            return
        if (self.audio_envelope & 0x08) != 0:
            if self.audio_volume < 15:
                self.audio_volume+=1
        elif self.audio_volume > 0:
            self.audio_volume-=1
        self.audio_4_envelope_length += (constants.SOUND_CLOCK / 64) *\
                                     (self.audio_envelope & 0x07)
                                         
    def mix_audio(self, buffer, length, output_terminal):
        for index in range(0, length, 2):
            self.audio_4_index += self.audio_4_frequency
            #polynomial
            if (self.audio_polynomial & 0x08) != 0:
                #  7 steps
                self.audio_4_index &= 0x7FFFFF
                polynomial = self.noise_step_7_table[self.audio_4_index >> 21] >>\
                             ((self.audio_4_index >> 16) & 31)
            else:
                #  15 steps
                self.audio_4_index &= 0x7FFFFFFF
                polynomial = self.noise_step_15_table[self.audio_4_index >> 21] >> \
                             ((self.audio_4_index >> 16) & 31)
            if (polynomial & 1) != 0:
                if (output_terminal & 0x80) != 0:
                    buffer[index + 0] -= self.audio_volume
                if (output_terminal & 0x08) != 0:
                    buffer[index + 1] -= self.audio_volume
            else:
                if (output_terminal & 0x80) != 0:
                    buffer[index + 0] += self.audio_volume
                if (output_terminal & 0x08) != 0:
                    buffer[index + 1] += self.audio_volume

    
    
# ------------------------------------------------------------------------------

        
class Sound(iMemory):

    def __init__(self, sound_driver):
        self.buffer          = [0] * 512
        self.outputLevel     = 0
        self.output_terminal = 0
        self.output_enable   = 0
        
        self.driver          = sound_driver
        self.sample_rate     =  self.driver.get_sample_rate()
        
        self.generate_frequency_table()
        self.create_audio_channels()
        
        self.reset()
        
    def create_audio_channels(self):
        self.channel1 = Channel1(self.sample_rate, self.frequency_table)
        self.channel2 = Channel2(self.sample_rate, self.frequency_table)
        self.channel3 = Channel3(self.sample_rate, self.frequency_table)
        self.channel4 = NoiseGenerator(self.sample_rate, self.frequency_table)
        
        
    def generate_frequency_table(self):
        self.frequency_table = [0] * 2048
         # frequency = (4194304 / 32) / (2048 - period) Hz
        for period in range(0, 2048):
            skip = (((constants.GAMEBOY_CLOCK << 10) / \
                   self.sample_rate) << 16) / (2048 - period)
            if skip >= (32 << 22):
                self.frequency_table[period] = 0
            else:
                self.frequency_table[period] = skip

    def reset(self):
        self.cycles = int(constants.GAMEBOY_CLOCK / constants.SOUND_CLOCK)
        self.frames = 0
        self.channel1.reset()
        self.channel2.reset()
        self.channel3.reset()
        self.channel4.reset()
        
        self.channel1.audio_index = 0
        self.channel2.audio_index = 0
        self.channel3.audio_index = 0
        self.channel4.audio_index = 0
        
        self.write(constants.NR10, 0x80)
        self.write(constants.NR11, 0x3F) #  0xBF
        self.write(constants.NR12, 0x00) #  0xF3
        self.write(constants.NR13, 0xFF)
        self.write(constants.NR14, 0xBF)

        self.write(constants.NR21, 0x3F)
        self.write(constants.NR22, 0x00)
        self.write(constants.NR23, 0xFF)
        self.write(constants.NR24, 0xBF)

        self.write(constants.NR30, 0x7F)
        self.write(constants.NR31, 0xFF)
        self.write(constants.NR32, 0x9F)
        self.write(constants.NR33, 0xFF)
        self.write(constants.NR34, 0xBF)

        self.write(constants.NR41, 0xFF)
        self.write(constants.NR42, 0x00)
        self.write(constants.NR43, 0x00)
        self.write(constants.NR44, 0xBF)

        self.write(constants.NR50, 0x00) #  0x77
        self.write(constants.NR51, 0xF0)
        self.write(constants.NR52, 0xFF) #  0xF0

        for address in range(0xFF30, 0xFF3F):
            write = 0xFF
            if (address & 1) == 0:
                write = 0x00
            self.write(address, write)
            
    def start(self):
        self.driver.start()

    def stop(self):
        self.driver.stop()

    def get_cycles(self):
        return self.cycles

    def emulate(self, ticks):
        ticks        = int(ticks)
        self.cycles -= ticks
        while (self.cycles <= 0):
            self.update_audio()
            if self.driver.is_enabled():
                self.mix_down_audio()
            self.cycles += constants.GAMEBOY_CLOCK / constants.SOUND_CLOCK
            
    def mix_down_audio(self):
        self.frames += self.driver.get_sample_rate()
        length      = (self.frames / constants.SOUND_CLOCK) << 1
        self.mix_audio(self.buffer, length)
        self.driver.write(self.buffer, length)
        self.frames %= constants.SOUND_CLOCK
        
    def read(self, address):
        address = int(address)
        if address==constants.NR10:
            return self.channel1.get_audio_sweep()
        elif address == constants.NR11:
            return self.channel1.get_audio_length()
        elif address == constants.NR12:
            return self.channel1.get_audio_envelope()
        elif address == constants.NR13:
            return self.channel1.get_audio_frequency()
        elif address == constants.NR14:
            return self.channel1.get_audio_playback()

        elif address == constants.NR21:
            return self.channel2.get_audio_length()
        elif address == constants.NR22:
            return self.channel2.get_audio_envelope()
        elif address==constants.NR23:
            return self.channel2.get_audio_frequency()
        elif address==constants.NR24:
            return self.channel2.get_audio_playback()

        elif address==constants.NR30:
            return self.channel3.get_audio_enable()
        elif address==constants.NR31:
            return self.channel3.get_audio_length()
        elif address==constants.NR32:
            return self.channel3.get_audio_level()
        elif address==constants.NR33:
            return self.channel4.get_audio_frequency()
        elif address==constants.NR34:
            return self.channel3.get_audio_playback()

        elif address==constants.NR41:
            return self.channel4.get_audio_length()
        elif address==constants.NR42:
            return self.channel4.get_audio_envelope()
        elif address==constants.NR43:
            return self.channel4.get_audio_polynomial()
        elif address==constants.NR44:
            return self.channel4.get_audio_playback()

        elif address==constants.NR50:
            return self.get_output_level()
        elif address==constants.NR51:
            return self.get_output_terminal()
        elif address==constants.NR52:
            return self.get_output_enable()

        elif address >= constants.AUD3WAVERAM and \
             address <= constants.AUD3WAVERAM + 0x3F:
            return self.channel3.get_audio_wave_pattern(address)
        return 0xFF

    def write(self, address, data):
        address = int(address)
        if address==constants.NR10:
            self.channel1.set_audio_sweep(data)
        elif address == constants.NR11:
            self.channel1.set_audio_length(data)
        elif address == constants.NR12:
            self.channel1.set_audio_envelope(data)
        elif address == constants.NR13:
            self.channel1.set_audio_frequency(data)
        elif address == constants.NR14:
            self.channel1.set_audio_playback(data)
        
        elif address == constants.NR21:
            self.channel2.set_audio_length(data)
        elif address == constants.NR22:
            self.channel2.set_audio_envelope(data)
        elif address == constants.NR23:
            self.channel2.set_audio_frequency(data)
        elif address == constants.NR24:
            self.channel2.set_audio_playback(data)
        
        elif address == constants.NR30:
            self.channel3.set_audio_enable(data)
        elif address == constants.NR31:
            self.channel3.set_audio_length(data)
        elif address == constants.NR32:
            self.channel3.set_audio_level(data)
        elif address == constants.NR33:
            self.channel3.set_audio_frequency(data)
        elif address == constants.NR34:
            self.channel3.set_audio_playback(data)
        
        elif address == constants.NR41:
            self.channel4.set_audio_length(data)
        elif address == constants.NR42:
            self.channel4.set_audio_envelope(data)
        elif address == constants.NR43:
            self.channel4.set_audio_polynomial(data)
        elif address == constants.NR44:
            self.channel4.set_audio_playback(data)
        
        elif address == constants.NR50:
            self.set_output_level(data)
        elif address == constants.NR51:
            self.set_output_terminal(data)
        elif address == constants.NR52:
            self.set_output_enable(data)
        
        elif address >= constants.AUD3WAVERAM and \
             address <= constants.AUD3WAVERAM + 0x3F:
            self.channel3.set_audio_wave_pattern(address, data)

    def update_audio(self):
        if (self.output_enable & 0x80) == 0:
            return
        if (self.output_enable & 0x01) != 0:
            self.channel1.update_audio()
        if (self.output_enable & 0x02) != 0:
            self.channel2.update_audio()
        if (self.output_enable & 0x04) != 0:
            self.channel3.update_audio()
        if (self.output_enable & 0x08) != 0:
            self.channel4.update_audio()

    def mix_audio(self, buffer, length):
        if (self.output_enable & 0x80) == 0:
            return
        if (self.output_enable & 0x01) != 0:
            self.channel1.mix_audio(buffer, length, self.output_terminal)
        if (self.output_enable & 0x02) != 0:
            self.channel2.mix_audio(buffer, length, self.output_terminal)
        if (self.output_enable & 0x04) != 0:
            self.channel3.mix_audio(buffer, length, self.output_terminal)
        if (self.output_enable & 0x08) != 0:
            self.channel4.mix_audio(buffer, length, self.output_terminal)

     # Output Control
    def get_output_level(self):
        return self.outputLevel

    def get_output_terminal(self):
        return self.output_terminal

    def get_output_enable(self):
        return self.output_enable

    def set_output_level(self, data):
        self.outputLevel = data

    def set_output_terminal(self, data):
        self.output_terminal = data

    def set_output_enable(self, data):
        self.output_enable = (self.output_enable & 0x7F) | (data & 0x80)
        if (self.output_enable & 0x80) == 0x00:
            self.output_enable &= 0xF0


class BogusSound(iMemory):
    """
        Used for development purposes
    """
    def __init__(self):
        pass
    
    def get_cycles(self):
        return 
    
    def reset(self):
        pass
    
    def get_cycles(self):
        return 0xFF
    
    def emulate(self, ticks):
        pass
    
    
# SOUND DRIVER -----------------------------------------------------------------


class SoundDriver(object):
    
    def __init__(self):
        self.enabled = True
        self.sample_rate = 44100
        self.channel_count = 2
        self.bits_per_sample = 8
    
    def is_enabled(self):
        return self.enabled
    
    def get_sample_rate(self):
        return self.sample_rate
    
    def get_channels(self):
        return self.channel_count
    
    def get_bits_per_sample(self):
        return self.bits_per_sample
    
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        pass
