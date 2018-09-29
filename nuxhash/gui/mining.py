from collections import defaultdict

import wx
import wx.dataview

from nuxhash import utils
from nuxhash.devices.nvidia import NvidiaDevice
from nuxhash.gui import main
from nuxhash.miners.excavator import Excavator


NVIDIA_COLOR = (66, 244, 69)


class MiningScreen(wx.Panel):

    def __init__(self, parent, *args, window=None, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self._window = window
        self._settings = None
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

        # Add mining panel.
        self._mining = MiningPanel(self)
        sizer.Add(self._mining, wx.SizerFlags().Border(wx.LEFT|wx.RIGHT|wx.TOP,
                                                       main.PADDING_PX)
                                               .Proportion(1.0)
                                               .Expand())

        bottom_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        sizer.Add(bottom_sizer, wx.SizerFlags().Border(wx.ALL, main.PADDING_PX)
                                               .Expand())

        # Add balance displays.
        balances = wx.FlexGridSizer(2, 2, main.PADDING_PX)
        balances.AddGrowableCol(1)
        bottom_sizer.Add(balances, wx.SizerFlags().Proportion(1.0).Expand())

        balances.Add(wx.StaticText(self, label='Daily revenue'))
        self._revenue = wx.StaticText(self,
                                      style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self._revenue.SetFont(self.GetFont().Bold())
        balances.Add(self._revenue, wx.SizerFlags().Expand())

        balances.Add(wx.StaticText(self, label='Address balance'))
        self._balance = wx.StaticText(self,
                                      style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self._balance.SetFont(self.GetFont().Bold())
        balances.Add(self._balance, wx.SizerFlags().Expand())

        bottom_sizer.AddSpacer(main.PADDING_PX)

        # Add start/stop button.
        self._startstop = wx.Button(self, label='Start Mining')
        bottom_sizer.Add(self._startstop, wx.SizerFlags().Expand()
                                                         .Center())
        self.Bind(wx.EVT_BUTTON, self.OnStartStop, self._startstop)

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value
        self._mining.settings = value

    def start_mining(self):
        self._startstop.SetLabel('Stop Mining')
        self._mining.start_mining()

    def stop_mining(self):
        self._revenue.SetLabel('')
        self._startstop.SetLabel('Start Mining')
        self._mining.stop_mining()

    def set_revenue(self, v):
        unit = self._settings['gui']['units']
        self._revenue.SetLabel(utils.format_balance(v, unit))

    def set_balance(self, v):
        unit = self._settings['gui']['units']
        self._balance.SetLabel(utils.format_balance(v, unit))

    def set_mining(self, event):
        total_revenue = sum(event.revenue.values())
        self.set_revenue(total_revenue)
        self._mining.display_status(speeds=event.speeds, revenue=event.revenue,
                                    devices=event.devices)

    def OnStartStop(self, event):
        self._window.toggle_mining()


class MiningPanel(wx.dataview.DataViewListCtrl):

    def __init__(self, parent, *args, **kwargs):
        wx.dataview.DataViewListCtrl.__init__(self, parent, *args, **kwargs)
        self.Disable()
        self.AppendTextColumn('Algorithm', width=wx.COL_WIDTH_AUTOSIZE)
        self.AppendColumn(
            wx.dataview.DataViewColumn('Devices', DeviceListRenderer(),
                                       1, align=wx.ALIGN_LEFT,
                                       width=wx.COL_WIDTH_AUTOSIZE),
            'string')
        self.AppendTextColumn('Speed', width=wx.COL_WIDTH_AUTOSIZE)
        self.AppendTextColumn('Revenue')

    @property
    def settings(self):
        return self._settings
    @settings.setter
    def settings(self, value):
        self._settings = value

    def start_mining(self):
        self.Enable()

    def stop_mining(self):
        self.Disable()
        self.DeleteAllItems()

    def display_status(self,
                       speeds=defaultdict(lambda: [0.0]),
                       revenue=defaultdict(lambda: 0.0),
                       devices=defaultdict(lambda: [])):
        self.DeleteAllItems()
        algorithms = list(speeds.keys())
        algorithms.sort(key=lambda algorithm: algorithm.name)
        for algorithm in algorithms:
            algo = '%s\n(%s)' % (algorithm.name, ', '.join(algorithm.algorithms))
            devices = ','.join([DeviceListRenderer.device_to_string(device)
                                for device in devices[algorithm]])
            speed = ',\n'.join([utils.format_speed(speed)
                                for speed in speeds[algorithm]])
            revenue = utils.format_balance(revenue[algorithm],
                                           self._settings['gui']['units'])
            self.AppendItem([algo, devices, speed, revenue])


class DeviceListRenderer(wx.dataview.DataViewCustomRenderer):

    CORNER_RADIUS = 5

    def __init__(self, *args, **kwargs):
        wx.dataview.DataViewCustomRenderer.__init__(self, *args, **kwargs)
        self.devices = []
        self._colordb = wx.ColourDatabase()

    def SetValue(self, value):
        vendors = {
            'N': 'nvidia'
            }
        self.devices = [{ 'name': s[2:], 'vendor': vendors[s[0]] }
                        for s in value.split(',')]
        return True

    def GetValue(self):
        tags = {
            'nvidia': 'N'
            }
        return ','.join(['%s:%s' % (tags[device['vendor']], device['name'])
                         for device in self.devices])

    def GetSize(self):
        boxes = [self.GetTextExtent(device['name']) for device in self.devices]
        return wx.Size((max(box.GetWidth() for box in boxes)
                        + DeviceListRenderer.CORNER_RADIUS*2),
                       (sum(box.GetHeight() for box in boxes)
                        + DeviceListRenderer.CORNER_RADIUS*2*len(boxes)
                        + DeviceListRenderer.CORNER_RADIUS*(len(boxes) - 1)))

    def Render(self, cell, dc, state):
        position = cell.GetPosition()
        for device in self.devices:
            box = self.GetTextExtent(device['name'])

            if device['vendor'] == 'nvidia':
                color = self._colordb.Find('LIME GREEN')
            else:
                color = self._colordb.Find('LIGHT GREY')
            dc.SetBrush(wx.Brush(color))
            dc.SetPen(wx.TRANSPARENT_PEN)
            shade_rect = wx.Rect(
                position,
                wx.Size(box.GetWidth() + DeviceListRenderer.CORNER_RADIUS*2,
                        box.GetHeight() + DeviceListRenderer.CORNER_RADIUS*2))
            dc.DrawRoundedRectangle(shade_rect, DeviceListRenderer.CORNER_RADIUS)

            text_rect = wx.Rect(
                wx.Point(position.x + DeviceListRenderer.CORNER_RADIUS,
                         position.y + DeviceListRenderer.CORNER_RADIUS),
                box)
            self.RenderText(device['name'], 0, text_rect, dc, state)

            position = wx.Point(position.x,
                                (position.y + box.GetHeight()
                                 + DeviceListRenderer.CORNER_RADIUS*2
                                 + DeviceListRenderer.CORNER_RADIUS))
        return True

    def device_to_string(device):
        if isinstance(device, NvidiaDevice):
            name = device.name
            name = name.replace('GeForce', '')
            name = name.replace('GTX', '')
            name = name.replace('RTX', '')
            name = name.strip()
            return 'N:%s' % name
        else:
            raise Exception('bad device instance')

