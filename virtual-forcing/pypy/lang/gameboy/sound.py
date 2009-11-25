"""
PyGirl Emulator
 
Audio Processor Unit (Sharp LR35902 APU)

There are two sound channels connected to the output
terminals SO1 and SO2. There is also a input terminal Vin
connected to the cartridge. It can be routed to either of
both output terminals. GameBoy circuitry allows producing
sound in four different ways:

  Quadrangular wave patterns with sweep and envelope functions.
  Quadrangular wave patterns with envelope functions.
  Voluntary wave patterns from wave RAM.
  White noise with an envelope function.

These four sounds can be controlled independantly and
then mixed separately for each of the output terminals.

 Sound registers may be set at all times while producing
sound.

When setting the initial value of the envelope and
restarting the length counter, set the initial flag to 1
and initialize the data.

 Under the following situations the Sound ON flag is
reset and the sound output stops:

 1. When the sound output is stopped by the length counter.
 2. When overflow occurs at the addition mode while sweep
    is operating at sound 1.

When the Sound OFF flag for sound 3 (bit 7 of NR30) is
set at 0, the cancellation of the OFF mode must be done
by setting the sound OFF flag to 1. By initializing
sound 3, it starts it's function.

When the All Sound OFF flag (bit 7 of NR52) is set to 0,
the mode registers for sounds 1,2,3, and 4 are reset and
the sound output stops. (NOTE: The setting of each sounds
mode register must be done after the All Sound OFF mode
is cancelled. During the All Sound OFF mode, each sound
mode register cannot be set.)

NOTE: DURING THE ALL SOUND OFF MODE, GB POWER CONSUMPTION
DROPS BY 16% OR MORE! WHILE YOUR PROGRAMS AREN'T USING
SOUND THEN SET THE ALL SOUND OFF FLAG TO 0. IT DEFAULTS
TO 1 ON RESET.

 These tend to be the two most important equations in
converting between Hertz and GB frequency registers:
(Sounds will have a 2.4% higher frequency on Super GB.)

    gb = 2048 - (131072 / Hz)

    Hz  = 131072 / (2048 - gb)
    
"""

from pypy.lang.gameboy.constants import *
from pypy.lang.gameboy.ram import iMemory

class Channel(object):

    index = 0
    length = 0
    frequency = 0
    
    def __init__(self, sample_rate, frequency_table):
        self.sample_rate     = int(sample_rate)
        self.frequency_table = frequency_table
        self.length    = 0
        self.envelope  = 0
        self.frequency = 0
        self.playback  = 0
        self.index     = 0
        self.length    = 0
        self.frequency = 0
        self.enabled   = False
        
    def reset(self):
        self.index = 0
        self.set_length(0xFF)
        self.set_playback(0xBF)
    
    
    def update_audio(self):
        self.update_enabled()
        self.update_envelope_and_volume()
        self.update_frequency_and_playback()
        
    def update_enabled(self):
        pass
        
    def update_envelope_and_volume(self):
        pass
        
    def update_frequency_and_playback(self):
        pass
        
    def get_length(self):
        return self.length
        
    def set_length(self, length):
        self.length = length

    def get_envelope(self):
        return self.envelope

    def get_frequency(self):
        return self.frequency

    def get_playback(self):
        return self.playback
        
    def set_playback(self, playback):
        self.playback = playback
        
    def mix_audio(self, buffer, length, output_terminal):
        pass
        

    
# ------------------------------------------------------------------------------

#SquareWaveGenerator
class SquareWaveChannel(Channel):
        # Audio Channel 1 int
    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
        self.sample_sweep    = 0
        self.raw_sample_sweep = 0
        self.index           = 0
        self.length          = 0
        self.raw_length = 0
        self.volume          = 0
        self.envelope_length = 0
        self.sample_sweep_length = 0
        self.frequency       = 0
        self.raw_frequency = 0
    
    def reset(self):
        Channel.reset(self)
        self.set_sweep(0x80)
        self.set_length(0x3F)
        self.set_envelope(0x00)
        self.set_frequency(0xFF)
        
        
     # Audio Channel 1
    def get_sweep(self):
        return self.raw_sample_sweep

    def set_sweep(self, data):
        self.raw_sample_sweep    = data
        self.sample_sweep_length = (SOUND_CLOCK / 128) * \
                                ((self.sample_sweep >> 4) & 0x07)
    def get_length(self):
        return self.raw_length
        
    def set_length(self, data):
        self.raw_length   = data
        self.length = (SOUND_CLOCK / 256) *  (64 - (self.raw_length & 0x3F))
                            
    def set_envelope(self, data):
        self.envelope = data
        if (self.playback & 0x40) != 0:
            return
        if (self.envelope >> 4) == 0:
            self.volume = 0
        elif self.envelope_length == 0 and (self.envelope & 0x07) == 0:
            self.volume = (self.volume + 1) & 0x0F
        else:
            self.volume = (self.volume + 2) & 0x0F


    def set_frequency(self, data):
        self.raw_frequency = data
        index = self.raw_frequency + ((self.playback & 0x07) << 8)
        self.frequency = self.frequency_table[index]

                                    
    def set_playback(self, data):
        self.playback = data
        index = self.raw_frequency + ((self.playback & 0x07) << 8)
        self.frequency = self.frequency_table[index]
        if (self.playback & 0x80) != 0:
            self.enabled = True
            if (self.playback & 0x40) != 0 and self.length == 0:
                self.length = (SOUND_CLOCK / 256) * \
                                    (64 - (self.length & 0x3F))
            self.sample_sweep_length = (SOUND_CLOCK / 128) * \
                                    ((self.raw_sample_sweep >> 4) & 0x07)
            self.volume = self.envelope >> 4
            self.envelope_length = (SOUND_CLOCK / 64) * (self.envelope & 0x07)

    def update_enable(self):
        if (self.playback & 0x40) != 0 and self.length > 0:
            self.length-=1
            if self.length <= 0:
                self.enabled = False
                
    def update_volume_and_envelope(self):
        if self.envelope_length <= 0: return
        self.envelope_length -= 1
        if self.envelope_length <= 0:
            if (self.envelope & 0x08) != 0:
                if (self.volume < 15):
                    self.volume += 1
            elif self.volume > 0:
                self.volume -= 1
            self.envelope_length += (SOUND_CLOCK / 64) * (self.envelope & 0x07)
                                             
    def update_frequency_and_playback(self):
        if self.sample_sweep_length <= 0:
            return
        self.sample_sweep_length-=1
        if self.sample_sweep_length > 0:
            return
        sweep_steps = (self.raw_sample_sweep & 0x07)
        if sweep_steps != 0:
            self.update_frequency(sweep_steps)
        self.sample_sweep_length += (SOUND_CLOCK / 128) * \
                                 ((self.raw_sample_sweep >> 4) & 0x07)
         
    def update_frequency(self, sweep_steps):
        frequency = ((self.playback & 0x07) << 8) + self.frequency
        if (self.raw_sample_sweep & 0x08) != 0:
            frequency -= frequency >> sweep_steps
        else:
            frequency += frequency >> sweep_steps
        if frequency < 2048:
            self.frequency = self.frequency_table[frequency]
            self.raw_frequency = frequency & 0xFF
            self.playback = (self.playback & 0xF8) + \
                                 ((frequency >> 8) & 0x07)
        else:
            self.frequency = 0
            self.enabled = False
            #self.output_enable &= ~0x01
                
    def mix_audio(self, buffer, length, output_terminal):
        wave_pattern = self.get_current_wave_pattern()
        for index in range(0, length, 3):
            self.index += self.frequency
           # if (self.index & (0x1F << 22)) >= wave_pattern:
                # output_terminal & 0x20 for the second SquareWaveChannel
            if (output_terminal & 0x10) != 0:
                buffer[index + 0] -= self.volume
            if (output_terminal & 0x01) != 0:
                buffer[index + 1] -= self.volume
            #else:
            #    if (output_terminal & 0x10) != 0:
            #        buffer[index + 0] += self.volume
            #    if (output_terminal & 0x01) != 0:
            #        buffer[index + 1] += self.volume
                    
    def get_current_wave_pattern(self):
        wave_pattern = 0x18
        if (self.raw_length & 0xC0) == 0x00:
            wave_pattern = 0x04
        elif (self.raw_length & 0xC0) == 0x40:
            wave_pattern = 0x08
        elif (self.raw_length & 0xC0) == 0x80:
            wave_pattern = 0x10
        return wave_pattern << 22
        

# ---------------------------------------------------------------------------
    
class VoluntaryWaveChannel(Channel):  

    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
        self.enable       = 0
        self.level        = 0
        self.index      = 0
        self.length     = 0
        self.raw_length = 0
        self.frequency  = 0
        self.raw_frequency = 0
        self.wave_pattern = [0]*16
    
    def reset(self):
        Channel.reset(self)
        self.set_enable(0x7F)
        self.set_length(0xFF)
        self.set_level(0x9F)
        self.set_frequency(0xFF)
        self.set_playback(0xBF)
              
    def get_enable(self):
        return self.enable

    def set_enable(self, data):
        self.enable = data & 0x80
        if (self.enable & 0x80) == 0:
            self.enabled = False
           
    def get_level(self):
        return self.level
        
    def set_level(self, data):
        self.level = data
        
    def get_length(self):
        return self.raw_length
        
    def set_length(self, data):
        self.raw_length = data
        self.length = (SOUND_CLOCK / 256) * (256 - self.raw_length)

    def get_frequency(self):
        return self.raw_frequency

    def set_frequency(self, data):
        self.raw_frequency = data
        index = ((self.playback & 0x07) << 8) + self.raw_frequency
        self.frequency = self.frequency_table[index] >> 1

    def set_playback(self, data):
        self.playback = data
        index = ((self.playback & 0x07) << 8) + self.raw_frequency
        self.frequency = self.frequency_table[index] >> 1
        if (self.playback & 0x80) != 0 and (self.enable & 0x80) != 0:
            self.enabled = True
            if (self.playback & 0x40) != 0 and self.length == 0:
                self.length = (SOUND_CLOCK / 256) * (256 - self.raw_length)
    
    def set_wave_pattern(self, address, data):
        self.wave_pattern[address & 0x0F] = data

    def get_wave_pattern(self, address):
        return self.wave_pattern[address & 0x0F] & 0xFF

    def update_audio(self):
        if (self.playback & 0x40) != 0 and self.length > 0:
            self.length-=1
            self.enabled = self.length <= 0
             #self.output_enable &= ~0x04

    def mix_audio(self, buffer, length, output_terminal):
        wave_pattern = self.get_current_wave_pattern()
        for index in range(0, length, 2):
            self.index += self.frequency
            sample = self.wave_pattern[(self.index >> 23) & 0x0F]
            if ((self.index & (1 << 22)) != 0):
                sample = (sample >> 0) & 0x0F
            else:
                sample = (sample >> 4) & 0x0F
            sample = int(((sample - 8) << 1) >> self.level)
            if (output_terminal & 0x40) != 0:
                buffer[index + 0] += sample
            if (output_terminal & 0x04) != 0:
                buffer[index + 1] += sample
    
    def get_current_wave_pattern(self):
        wave_pattern = 2
        if (self.level & 0x60) == 0x00:
            wave_pattern = 8
        elif (self.level & 0x60) == 0x20:
            wave_pattern = 0
        elif (self.level & 0x60) == 0x40:
            wave_pattern = 1
        return wave_pattern << 22
            
# --------------------------------------------------------------------------- 

class NoiseGenerator(Channel):
        
    def __init__(self, sample_rate, frequency_table):
        Channel.__init__(self, sample_rate, frequency_table)
            # Audio Channel 4 int
        self.length          = 0
        self.polynomial      = 0
        self.index           = 0
        self.length          = 0
        self.raw_length      = 0
        self.volume          = 0
        self.envelope_length = 0
        self.frequency       = 0
        self.generate_noise_frequency_ratio_table()
        self.generate_noise_tables()
    
    def reset(self):
        Channel.reset(self)
        self.set_length(0xFF)
        self.set_envelope(0x00)
        self.set_polynomial(0x00)
        self.set_playback(0xBF)
        
    def generate_noise_frequency_ratio_table(self):
         # Polynomial Noise Frequency Ratios
         # 4194304 Hz * 1 / 2^3 * 2 4194304 Hz * 1 / 2^3 * 1 4194304 Hz * 1 / 2^3 *
         # 1 / 2 4194304 Hz * 1 / 2^3 * 1 / 3 4194304 Hz * 1 / 2^3 * 1 / 4 4194304 Hz *
         # 1 / 2^3 * 1 / 5 4194304 Hz * 1 / 2^3 * 1 / 6 4194304 Hz * 1 / 2^3 * 1 / 7
        self.noiseFreqRatioTable = [0] * 8
        sampleFactor = ((1 << 16) / self.sample_rate)
        self.noiseFreqRatioTable[0] = GAMEBOY_CLOCK * sampleFactor
        for ratio in range(1, 8):
            divider = 2 * ratio
            self.noiseFreqRatioTable[ratio] = (GAMEBOY_CLOCK / divider) * \
                                              sampleFactor

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
            if (index & 0x1F) == 0:
                self.noise_step_7_table[index >> 5] = 0
            self.noise_step_7_table[index >> 5] |= (polynomial & 0x01) << \
                                                (index & 0x1F)
            
    def create_15_step_noise_table(self):
        #  15 steps&
        self.noise_step_15_table = [0]*1024
        polynomial = 0x7FFF
        for index in range(0, 0x7FFF):
            polynomial = (((polynomial << 14) ^ (polynomial << 13)) & \
                         0x4000) | (polynomial >> 1)
            if (index & 0x1F) == 0:
                self.noise_step_15_table[index >> 5] = 0
            self.noise_step_15_table[index >> 5] |= (polynomial & 0x01) << \
                                                 (index & 0x1F)
    
    def get_length(self):
        return self.raw_length

    def set_length(self, data):
        self.raw_length = data
        self.length = (SOUND_CLOCK / 256) * (64 - (self.length & 0x3F))

    def set_envelope(self, data):
        self.envelope = data
        if (self.playback & 0x40) is not 0:
            return
        if (self.envelope >> 4) == 0:
            self.volume = 0
        elif self.envelope_length == 0 and (self.envelope & 0x07) == 0:
            self.volume = (self.volume + 1) & 0x0F
        else:
            self.volume = (self.volume + 2) & 0x0F

    def get_polynomial(self):
        return self.polynomial

    def set_polynomial(self, data):
        self.polynomial = data
        if (self.polynomial >> 4) <= 12:
            freq = self.noiseFreqRatioTable[self.polynomial & 0x07]
            self.frequency = freq >> ((self.polynomial >> 4) + 1)
        else:
            self.frequency = 0

    def get_playback(self):
        return self.playback
        
    def set_playback(self, data):
        self.playback = data
        if (self.playback & 0x80) == 0:
            return
        self.enabled = True
        if (self.playback & 0x40) != 0 and self.length == 0:
            self.length = (SOUND_CLOCK / 256) *  (64 - (self.length & 0x3F))
        self.volume = self.envelope >> 4
        self.envelope_length = (SOUND_CLOCK / 64) * (self.envelope & 0x07)
        self.index = 0
    
    def update_enabled(self):
        if (self.playback & 0x40) != 0 and self.length > 0:
            self.length-=1
            self.enabled = self.length <= 0
            #self.output_enable &= ~0x08
                
    def update_envelope_and_volume(self):
        if self.envelope_length <= 0:
            return
        self.envelope_length -= 1
        if self.envelope_length > 0:
            return
        if (self.envelope & 0x08) != 0:
            if self.volume < 15:
                self.volume += 1
        elif self.volume > 0:
            self.volume -= 1
        self.envelope_length += (SOUND_CLOCK / 64) * (self.envelope & 0x07)
                                         
    def mix_audio(self, buffer, length, output_terminal):
        for index in range(0, length, 2):
            self.index += self.frequency
            #polynomial
            if (self.polynomial & 0x08) != 0:
                #  7 steps
                self.index &= 0x7FFFFF
                polynomial = self.noise_step_7_table[self.index >> 21] >>\
                             ((self.index >> 16) & 0x1F)
            else:
                #  15 steps
                self.index &= 0x7FFFFFFF
                polynomial = self.noise_step_15_table[self.index >> 21] >> \
                             ((self.index >> 16) & 0x1F)
            if (polynomial & 1) != 0:
                if (output_terminal & 0x80) != 0:
                    buffer[index + 0] -= self.volume
                if (output_terminal & 0x08) != 0:
                    buffer[index + 1] -= self.volume
            else:
                if (output_terminal & 0x80) != 0:
                    buffer[index + 0] += self.volume
                if (output_terminal & 0x08) != 0:
                    buffer[index + 1] += self.volume

    
    
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
        self.create_channels()
        
        self.reset()
        
    def create_channels(self):
        self.channel1 = SquareWaveChannel(self.sample_rate, self.frequency_table)
        self.channel2 = SquareWaveChannel(self.sample_rate, self.frequency_table)
        self.channel3 = VoluntaryWaveChannel(self.sample_rate, self.frequency_table)
        self.channel4 = NoiseGenerator(self.sample_rate, self.frequency_table)
        self.channels = [self.channel1, self.channel2, self.channel3, self.channel4]
        
        
    def generate_frequency_table(self):
        self.frequency_table = [0] * 2048
         # frequency = (4194304 / 32) / (2048 - period) Hz
        for period in range(0, 2048):
            skip = (((GAMEBOY_CLOCK << 10) / \
                   self.sample_rate) << 16) / (2048 - period)
            if skip >= (32 << 22):
                self.frequency_table[period] = 0
            else:
                self.frequency_table[period] = skip

    def reset(self):
        self.cycles = int(GAMEBOY_CLOCK / SOUND_CLOCK)
        self.frames = 0
        self.channel1.reset()
        self.channel2.reset()
        self.channel3.reset()
        self.channel4.reset()

        self.set_output_level(0x00)
        self.set_output_terminal(0xF0)
        self.set_output_enable(0xFF)

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
            self.cycles += GAMEBOY_CLOCK / SOUND_CLOCK
            
    def mix_down_audio(self):
        self.frames += self.driver.get_sample_rate()
        length      = (self.frames / SOUND_CLOCK) << 1
        self.mix_audio(self.buffer, length)
        self.driver.write(self.buffer, length)
        self.frames %= SOUND_CLOCK
        
    def read(self, address):
        # TODO map the read/write in groups directly to the channels
        address = int(address)
        if address==NR10:
            return self.channel1.get_sweep()
        elif address == NR11:
            return self.channel1.get_length()
        elif address == NR12:
            return self.channel1.get_envelope()
        elif address == NR13:
            return self.channel1.get_frequency()
        elif address == NR14:
            return self.channel1.get_playback()

        elif address == NR21:
            return self.channel2.get_length()
        elif address == NR22:
            return self.channel2.get_envelope()
        elif address==NR23:
            return self.channel2.get_frequency()
        elif address==NR24:
            return self.channel2.get_playback()

        elif address==NR30:
            return self.channel3.get_enable()
        elif address==NR31:
            return self.channel3.get_length()
        elif address==NR32:
            return self.channel3.get_level()
        elif address==NR33:
            return self.channel4.get_frequency()
        elif address==NR34:
            return self.channel3.get_playback()

        elif address==NR41:
            return self.channel4.get_length()
        elif address==NR42:
            return self.channel4.get_envelope()
        elif address==NR43:
            return self.channel4.get_polynomial()
        elif address==NR44:
            return self.channel4.get_playback()

        elif address==NR50:
            return self.get_output_level()
        elif address==NR51:
            return self.get_output_terminal()
        elif address==NR52:
            return self.get_output_enable()

        elif address >= AUD3WAVERAM and address <= AUD3WAVERAM + 0x3F:
            return self.channel3.get_wave_pattern(address)
        return 0xFF

    def write(self, address, data):
        address = int(address)
        if address == NR10:
            self.channel1.set_sweep(data)
        elif address == NR11:
            self.channel1.set_length(data)
        elif address == NR12:
            self.channel1.set_envelope(data)
        elif address == NR13:
            self.channel1.set_frequency(data)
        elif address == NR14:
            self.channel1.set_playback(data)
        
        elif address == NR21:
            self.channel2.set_length(data)
        elif address == NR22:
            self.channel2.set_envelope(data)
        elif address == NR23:
            self.channel2.set_frequency(data)
        elif address == NR24:
            self.channel2.set_playback(data)
        
        elif address == NR30:
            self.channel3.set_enable(data)
        elif address == NR31:
            self.channel3.set_length(data)
        elif address == NR32:
            self.channel3.set_level(data)
        elif address == NR33:
            self.channel3.set_frequency(data)
        elif address == NR34:
            self.channel3.set_playback(data)
        
        elif address == NR41:
            self.channel4.set_length(data)
        elif address == NR42:
            self.channel4.set_envelope(data)
        elif address == NR43:
            self.channel4.set_polynomial(data)
        elif address == NR44:
            self.channel4.set_playback(data)
        
        elif address == NR50:
            self.set_output_level(data)
        elif address == NR51:
            self.set_output_terminal(data)
        elif address == NR52:
            self.set_output_enable(data)
        
        elif address >= AUD3WAVERAM and address <= AUD3WAVERAM + 0x3F:
            self.channel3.set_wave_pattern(address, data)

    def update_audio(self):
        if (self.output_enable & 0x80) != 0:
            for channel in self.channels:
                if channel.enabled:
                    channel.update_audio()

    def mix_audio(self, buffer, length):
        if (self.output_enable & 0x80) != 0:
            for channel in self.channels:
                if channel.enabled:
                    channel.mix_audio(buffer, length, self.output_terminal)

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
        # TODO map directly to the channels
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
