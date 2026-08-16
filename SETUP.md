## References

- <https://www.waveshare.com/wiki/7.3inch_e-Paper_HAT_(E)_Manual>
- https://github.com/fatihak/InkyPi/blob/main/docs/community.md
- https://github.com/waveshareteam/e-Paper

## Raspberry Pi setup

```bash
sudo apt install git swig python3-setuptools

# GPIO backend
git clone https://github.com/joan2937/lg
cd lg && make && sudo make install && sudo ldconfig && cd ..

# GPIO permissions
getent group gpio > /dev/null || sudo groupadd gpio
grep -rq 'KERNEL=="gpiochip' /etc/udev/rules.d /lib/udev/rules.d /usr/lib/udev/rules.d 2>/dev/null \
  || echo 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/99-gpio.rules

sudo usermod -aG gpio "$USER"
sudo udevadm control --reload-rules && sudo udevadm trigger

# SPI (Debian's raspi-firmware regenerates config.txt, so edit its source instead)
grep -q '^dtoverlay=pi4-spidev' /etc/default/raspi-firmware-custom 2>/dev/null \
  || echo 'dtoverlay=pi4-spidev' | sudo tee -a /etc/default/raspi-firmware-custom
sudo env DEB_MAINT_PARAMS=configure /etc/kernel/postinst.d/z50-raspi-firmware "$(uname -r)"

# SPI permissions
getent group spi > /dev/null || sudo groupadd spi
grep -rq 'KERNEL=="spidev' /etc/udev/rules.d /lib/udev/rules.d /usr/lib/udev/rules.d 2>/dev/null \
  || echo 'SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"' | sudo tee /etc/udev/rules.d/99-spi.rules
sudo usermod -aG spi "$USER"

sudo reboot
```
