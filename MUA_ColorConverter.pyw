from tkinter import *
from tkinter import colorchooser, font, messagebox, ttk
from colorsys import rgb_to_hls, hls_to_rgb
from contextlib import suppress
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable
import sys, time

if sys.platform.startswith('win'):
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2)

# import settings > which includes initial color, etc.
SAVED_COLOR = 'white'
STD_SHADES = [0.9, 0.8, 0.7, 0.4, 0.3]
STD_COLORS = [
    '#FF0000', '#FFC000', '#FFFF00', '#00B050',
    '#0070C0', '#7030A0', '#FFFFFF', '#000000'
]
OUTSIDERS_COLORS = [
    '#800000', '#FF0000', '#ff8000', '#FFFF00', '#90ff90', '#00ff00', '#00ffff', '#a3ceff', '#6a88ff', '#0060ff', '#0000ff', '#300090', '#9060ff', '#9020ff', '#FF1F86', '#ff70b0', '#7c552c', '#ffee6e', '#e7e7ed', '#FFFFFF', '#a5a5a5', '#000000'
]


def color_to_model(c: any, inmodel: str = None, outmodel: str = 'hex'):
    if inmodel == outmodel: return c
    h = c[1:] if inmodel == 'hex' else f'{int(c):#08x}'[2:] if inmodel == 'dec' else bytes.fromhex(f'{int(c):#08x}'[2:])[::-1].hex() if inmodel == 'rdec' else f'{int(c[0]):02x}{int(c[1]):02x}{int(c[2]):02x}' if inmodel == 'rgb' else hsl_to_hex(*c)[1:] if inmodel == 'hsl' else 'ffffff'
    return f'#{h}' if outmodel == 'hex' else (int(h[i:i+2], 16) for i in (0, 2, 4)) if outmodel == 'rgb' else int(f'0x{h}', 16) if outmodel == 'dec' else int(f'0x{h[4:6] + h[2:4] + h[:2]}', 16) if outmodel == 'rdec' else hex_to_hsl(f'#{h}') if outmodel == 'hsl' else None
    # this seems to be useless: ImageColor.getrgb(f'rgb({c[0]},{c[1]},{c[2]})')

def color_to_hex(root, colorname: str) -> str:
    r, g, b = root.winfo_rgb(colorname)
    return f'#{int(r/257):02x}{int(g/257):02x}{int(b/257):02x}'

def hex_to_hsl(hx: str) -> tuple:
    r, g, b = (int(hx[i:i+2], 16) for i in (1, 3, 5))
    hls = rgb_to_hls(r/255, g/255, b/255)
    h = int(hls[0]*360) # HUE
    l = int(hls[1]*100) # LUM
    s = int(hls[2]*100) # SAT
    return h, s, l

def hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = hls_to_rgb(h/360, l/100, s/100)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def rgb_to_decimal(rgb: tuple) -> int:
    r, g, b = rgb
    return (r << 16) | (g << 8) | b

def contrast_color(r: int, g: int, b: int, darkcolor: str = '#000', lightcolor: str = '#fff') -> str:
    return darkcolor if (((0.299 * r) + (0.587 * g) + (0.114 * b))/255) > 0.5 else lightcolor

def lum_to_alpha(rgb: tuple, l: float, bg: float = 255) -> str:
    a = min(l * 2.2, 1)
    ai = 1 - a
    r, g, b = (min(max(int(bg * ai + c * a), 0), 255) for c in rgb)
    return f'#{r:02x}{g:02x}{b:02x}'

def blend_subtractive_rdec(rgb: tuple, a: float = 1, bg: float = 255) -> str:
    # additive (min(int(bg + c * a), 255) for c in rgb)
    r, g, b = (max(int(bg - c * a), 0) for c in rgb)
    return int(f'0x{b:02x}{g:02x}{r:02x}', 16)

def scale_size(widget, sizes: list) -> list:
    factor = widget.tk.call('tk', 'scaling') / 1.33398982438864281
    return [int(x * factor) for x in sizes]


class ttkDecimalColorEntry(ttk.Entry):
    '''A Entry widget that only accepts digits'''
    def __init__(self, master=None, textvariable=None, justify=None, **kwargs):
        self.justify = justify if justify else RIGHT
        textvariable.trace_add('write', self.validate)
        ttk.Entry.__init__(self, master, textvariable=textvariable, justify=self.justify, **kwargs)
        self.get, self.set = textvariable.get, textvariable.set
    def validate(self, *args):
        value = self.get()
        if value and (not value.isdigit() or int(value) > 16777215):
            self.set(16777215) # hash(value)[-8:]

class ToolTipStatus(Enum):
    OUTSIDE = auto()
    INSIDE = auto()
    VISIBLE = auto()

class Binding:
    def __init__(self, widget: Widget, binding_name: str, functor: Callable) -> None:
        self._widget = widget
        self._name: str = binding_name
        self._id: str = self._widget.bind(binding_name, functor, add='+')

    def unbind(self) -> None:
        self._widget.unbind(self._name, self._id)

class ToolTip(Toplevel):
    """
    https://github.com/gnikit/tkinter-tooltip
    Creates a ToolTip (pop-up) widget for tkinter
    Allows for `**kwargs` to be passed on both the parent frame and the ToolTip message
    """

    DEFAULT_PARENT_KWARGS = {'bg': 'black', 'padx': 1, 'pady': 1}
    DEFAULT_MESSAGE_KWARGS = {'aspect': 1000}

    def __init__(
        self,
        widget: Widget,
        msg: str,
        delay: float = 0.0,
        follow: bool = True,
        x_offset: int = +10,
        y_offset: int = +10,
        parent_kwargs: dict | None = None,
        **message_kwargs: Any,
    ):
        self.widget = widget
        # ToolTip should have the same parent as the widget unless stated
        # otherwise in the `parent_kwargs`
        Toplevel.__init__(self, **(parent_kwargs or self.DEFAULT_PARENT_KWARGS))
        self.withdraw()  # Hide initially in case there is a delay
        # Disable ToolTip's title bar
        self.overrideredirect(True)

        # StringVar instance for msg string|function
        self.msg_var = StringVar(value=msg)
        self.msg = msg
        self.delay = delay
        self.follow = follow
        self.x_offset = x_offset
        self.y_offset = y_offset
        # visibility status of the ToolTip inside|outside|visible
        self.status = ToolTipStatus.OUTSIDE
        self.last_moved = 0
        # use Message widget to host ToolTip
        self.message_kwargs: dict = self.DEFAULT_MESSAGE_KWARGS.copy()
        self.message_kwargs.update(message_kwargs)
        self.message_widget = Message(
            self,
            textvariable=self.msg_var,
            **self.message_kwargs,
        )
        self.message_widget.grid()
        self.bindigs = self._init_bindings()

    def _init_bindings(self) -> list[Binding]:
        """Initialize the bindings."""
        bindings = [
            Binding(self.widget, '<Enter>', self.on_enter),
            Binding(self.widget, '<Leave>', self.on_leave),
            Binding(self.widget, '<ButtonPress>', self.on_leave),
        ]
        if self.follow:
            bindings.append(
                Binding(self.widget, '<Motion>', self._update_tooltip_coords)
            )
        return bindings

    def destroy(self):
        """Destroy the ToolTip and unbind all the bindings."""
        with suppress(TclError):
            for b in self.bindigs:
                b.unbind()
            self.bindigs.clear()
            super().destroy()

    def on_enter(self, event: Event):
        """Processes motion within the widget including entering and moving."""
        self.last_moved = time.time()
        self.status = ToolTipStatus.INSIDE
        self._update_tooltip_coords(event)
        self.after(int(self.delay * 1000), self._show)

    def on_leave(self, event: Event | None = None):
        """Hides the ToolTip."""
        self.status = ToolTipStatus.OUTSIDE
        self.withdraw()

    def _update_tooltip_coords(self, event: Event):
        """Updates the ToolTip's position."""
        self.geometry(f'+{event.x_root + self.x_offset}+{event.y_root + self.y_offset}')

    def _update_message(self):
        self.msg_var.set(self.msg)

    def _show(self):
        """Displays the ToolTip."""
        if (
            self.status == ToolTipStatus.INSIDE
            and time.time() - self.last_moved > self.delay
        ):
            self.status = ToolTipStatus.VISIBLE

        if self.status == ToolTipStatus.VISIBLE:
            self.msg_var.set(self.msg)
            self.deiconify()

# color picker by TtkBootstrap
# https://github.com/israel-dryer/ttkbootstrap/tree/master
class ColorChooser(ttk.Frame):
    """A class which creates a color chooser widget
    
    ![](../../assets/dialogs/querybox-get-color.png)    
    """

    def __init__(self, master, initialcolor=None, padding=None, blend_mode=None, textvariable=None):
        super().__init__(master, padding=padding)
        self.style = ttk.Style(master)
        self.initialcolor = color_to_hex(self, initialcolor) if initialcolor else master['bg']
        self.blend_mode = blend_mode or 'alpha'
        self.textvariable = textvariable

        self.tframe = ttk.Frame(self, padding=5)
        self.tframe.pack(fill=X)
        self.bframe = ttk.Frame(self, padding=(5, 0, 5, 5))
        self.bframe.pack(fill=X)

        self.tabview = ttk.Notebook(self.tframe)
        self.tabview.pack(fill=BOTH)

        # color variables
        self.hue = IntVar()
        self.sat = IntVar()
        self.lum = IntVar()
        self.red = IntVar()
        self.grn = IntVar()
        self.blu = IntVar()
        self.hex = StringVar(value=self.initialcolor)
        self.dec = StringVar()
        self.rdec = StringVar()

        # widget sizes (adjusted by widget scaling, not)
        self.spectrum_height, self.spectrum_width, self.spectrum_point = scale_size(self, [240, 360, 12])

        # build widgets
        spectrum_frame = ttk.Frame(self.tabview)
        self.color_spectrum = self.create_spectrum(spectrum_frame)
        self.color_spectrum.pack(fill=X, expand=YES, side=TOP)
        self.tabview.add(spectrum_frame, text='Advanced')
        self.standard_swatches = self.create_swatches(
            self.tabview, STD_COLORS)
        self.tabview.add(self.standard_swatches, text='Standard')
        self.outsider_swatches = self.create_swatches_ns(
            self.tabview, OUTSIDERS_COLORS)
        self.tabview.add(self.outsider_swatches, text='Outsider')
        self.tabview.add(ttk.Frame(self.tabview), text='More...')
        self.tabview.bind(
            sequence='<<NotebookTabChanged>>',
            func=self.os_colorchooser,
            add='+'
        )
        self.luminance_scale = self.create_luminance_scale(self.tframe)
        self.luminance_scale.pack(fill=X)

        self.create_spectrum_indicator()
        self.create_luminance_indicator()

        preview_frame = self.create_preview(self.bframe)
        preview_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 5))
        self.color_entries = self.create_value_inputs(self.bframe)
        self.color_entries.pack(side=RIGHT)

        self.sync_color_values(model='hex', color=self.initialcolor)


    def create_spectrum(self, master):
        """Create the color spectrum canvas"""
        # canvas and point dimensions
        width = self.spectrum_width
        height = self.spectrum_height
        xf = yf = self.spectrum_point

        # create canvas widget and binding
        canvas = Canvas(master, width=width, height=height, cursor='tcross')
        canvas.bind('<B1-Motion>', self.on_spectrum_interaction, add='+')
        canvas.bind('<Button-1>', self.on_spectrum_interaction, add='+')

        # add color points
        for x, colorx in enumerate(range(0, width, xf)):
            for y, colory in enumerate(range(0, height, yf)):
                h, s, l = self.hsl_from_coords(colorx, colory)
                fill = hsl_to_hex(h, s, l)
                canvas.create_rectangle(x*xf, y*yf, (x*xf)+xf, (y*yf)+yf, fill=fill, width=0)
        return canvas

    def create_spectrum_indicator(self):
        """Create a square indicator that will move to the position of the selected color"""
        s, width = scale_size(self, [10, 2])
        tag = 'spectrum-indicator'
        self.color_spectrum.create_rectangle(0, 0, s, s, width=width, tags=[tag])
        self.color_spectrum.tag_raise(tag)

    # widget builder methods
    def create_swatches(self, master, colors):
        """Create color combinations"""
        color_rows = [colors]
        for l in STD_SHADES:
            lum = int(l*100)
            row = []
            for color in colors:
                h, s, _ = hex_to_hsl(color)
                row.append(hsl_to_hex(h, s, int(l*100)))
            color_rows.append(row)

        return self.create_swatches_grid(master, color_rows)

    def create_swatches_ns(self, master, colors):
        """Create color set without shades"""
        color_rows = []
        i = 1
        for _ in range(len(STD_SHADES) + 1):
            row = []
            for _ in STD_COLORS:
                row.append(colors[:i][-1])
                i += 1
            color_rows.append(row)

        return self.create_swatches_grid(master, color_rows)

    def create_swatches_grid(self, master, color_rows):
        """Create a grid of color swatches"""
        boxpadx = 2
        boxpady = 1
        boxwidth = int((self.spectrum_width - boxpadx * 15)) / len(STD_COLORS)
        boxheight = int((self.spectrum_height - boxpady) / (len(STD_SHADES) + 1))
        lastcol = len(color_rows[0]) - 1
        container = ttk.Frame(master)

        # themed colors - regular colors
        for row in color_rows:
            rowframe = ttk.Frame(container)
            for j, color in enumerate(row):
                swatch = Frame(
                    master=rowframe,
                    bg=color,
                    width=boxwidth,
                    height=boxheight
                ) # autostyle=False
                swatch.bind('<Button-1>', self.on_press_swatch)
                if j == 0:
                    swatch.pack(side=LEFT, padx=(0, boxpadx))
                elif j == lastcol:
                    swatch.pack(side=LEFT, padx=(boxpadx, 0))
                else:
                    swatch.pack(side=LEFT, padx=boxpadx)
            rowframe.pack(fill=X, expand=YES)

        return container

    def create_luminance_scale(self, master):
        """Create the color luminance canvas"""
        # widget dimensions
        height = xf = self.spectrum_point
        width = self.spectrum_width

        canvas = Canvas(master, height=height, width=width)

        # add interactions to scale
        for x, l in enumerate(range(0, width, xf)):
            canvas.create_rectangle(x*xf, 0, (x*xf)+xf, height, width=0, tags=[f'color{x}'])
            canvas.bind('<B1-Motion>', self.on_luminance_interaction, add='+')
            canvas.bind('<Button-1>', self.on_luminance_interaction, add='+')
        return canvas

    def create_luminance_indicator(self):
        """Create an indicator that will move in the position of the luminance value"""
        x1 = int(0.5 * self.spectrum_width) - \
            ((self.spectrum_point - 2)//2)
        tag = 'luminance-indicator'
        self.luminance_scale.create_rectangle(
            x1, 0, x1 + self.spectrum_point, self.spectrum_point - 3,
            fill='white',
            outline='black',
            tags=[tag]
        )
        self.luminance_scale.tag_raise(tag)

    def create_preview(self, master):
        """Create a preview and decimals"""
        container = ttk.Frame(master)

        # set the border color to match the notebook border color (default ttk doesn't have border color)
        bordercolor = '#555555' # self.style.lookup(self.tabview.cget('style') or 'TNotebook', 'bordercolor')

        # the frame and label for the new color
        if self.blend_mode == 'alpha':
            self.preview = Frame(
                master=container,
                relief=FLAT,
                bd=2,
                highlightthickness=1,
                highlightbackground=bordercolor
            ) # autostyle=False
            self.preview.pack(side=TOP, fill=BOTH, expand=YES, padx=(2, 0))
            self.preview_lbl = Label(
                master=self.preview,
                text='Preview',
                width=7
            ) # autostyle=False
            self.preview_lbl.pack(anchor=N, pady=5)
        else:
            cb_preview = ttk.Frame(master=container)
            cb_preview.pack(side=TOP, fill=BOTH, expand=YES, padx=(6, 0))
            s = 20
            d = 240
            self.checkerboard = Canvas(
                cb_preview,
                #highlightbackground=self.bg_color[0],
                width=d,
                height=d
            )
            for xi, x in enumerate(range(0, d, s)):
                for yi, y in enumerate(range(0, d, s)):
                    self.checkerboard.create_rectangle(x, y, x+s, y+s, width=0, tags=['cb_light' if (xi + yi) % 2 else 'cb_dark'])
            self.checkerboard.place(relwidth=1, relheight=1)

        # Decimal fields
        decimals = ttk.Frame(container)
        decimals.pack(anchor=SE, padx=(2, 0))
        ent_dec = ttkDecimalColorEntry(decimals, width=16, textvariable=self.dec)
        ent_dec.grid(row=0, column=1, padx=4, pady=2, sticky=EW)
        fr_rdec = ttk.Frame(decimals, style='custom.TFrame')
        fr_rdec.grid(row=1, column=1, padx=3, pady=1, sticky=EW)
        ent_rdec = ttkDecimalColorEntry(fr_rdec, width=16, textvariable=self.rdec)
        ent_rdec.pack(fill=BOTH, expand=2, padx=1, pady=1)
        
        lbl_cnf = {'master': decimals, 'anchor': E}
        ttk.Label(**lbl_cnf, text='Decimal RGB').grid(row=0, column=0, sticky=E)
        ttk.Label(**lbl_cnf, text='Decimal BGR', style='bold.TLabel').grid(row=1, column=0, sticky=E)
        for sequence in ['<Return>', '<KP_Enter>']:
            ent_dec.bind(
                sequence=sequence,
                func=lambda _: self.sync_color_values('dec'),
                add='+'
            )
            ent_rdec.bind(
                sequence=sequence,
                func=lambda _: self.sync_color_values('rdec'),
                add='+'
            )
        self.update()
        if self.blend_mode != 'alpha': cb_preview.configure(height=decimals.winfo_height(), width=decimals.winfo_width())

        return container

    def create_value_inputs(self, master):
        """Create color value input widgets"""
        container = ttk.Frame(master)
        for x in range(4):
            container.columnconfigure(x, weight=1)

        # value labels
        lbl_cnf = {'master': container, 'anchor': E}
        ttk.Label(**lbl_cnf, text='Hue').grid(row=0, column=0, sticky=E)
        ttk.Label(**lbl_cnf, text='Sat').grid(row=1, column=0, sticky=E)
        ttk.Label(**lbl_cnf, text='Lum').grid(row=2, column=0, sticky=E)
        ttk.Label(**lbl_cnf, text='Hex').grid(row=3, column=0, sticky=E)
        ttk.Label(**lbl_cnf, text='Red').grid(row=0, column=2, sticky=E)
        ttk.Label(**lbl_cnf, text='Green').grid(row=1, column=2, sticky=E)
        ttk.Label(**lbl_cnf, text='Blue').grid(row=2, column=2, sticky=E)

        # value spinners and entry widgets
        rgb_cnf = {'master': container, 'from_': 0, 'to': 255, 'width': 6}
        sl_cnf = {'master': container, 'from_': 0, 'to': 100, 'width': 6}
        hue_cnf = {'master': container, 'from_': 0, 'to': 360, 'width': 6}
        sb_hue = ttk.Spinbox(**hue_cnf, textvariable=self.hue)
        sb_hue.grid(row=0, column=1, padx=4, pady=2, sticky=EW)
        sb_sat = ttk.Spinbox(**sl_cnf, textvariable=self.sat)
        sb_sat.grid(row=1, column=1, padx=4, pady=2, sticky=EW)
        sb_lum = ttk.Spinbox(**sl_cnf, textvariable=self.lum)
        sb_lum.grid(row=2, column=1, padx=4, pady=2, sticky=EW)
        sb_red = ttk.Spinbox(**rgb_cnf, textvariable=self.red)
        sb_red.grid(row=0, column=3, padx=4, pady=2, sticky=EW)
        sb_grn = ttk.Spinbox(**rgb_cnf, textvariable=self.grn)
        sb_grn.grid(row=1, column=3, padx=4, pady=2, sticky=EW)
        sb_blu = ttk.Spinbox(**rgb_cnf, textvariable=self.blu)
        sb_blu.grid(row=2, column=3, padx=4, pady=2, sticky=EW)
        ent_hex = ttk.Entry(container, textvariable=self.hex)
        ent_hex.grid(row=3, column=1, padx=4, columnspan=3, pady=2, sticky=EW)

        # event binding for updating colors on value change
        for sequence in ['<Return>', '<KP_Enter>']:
            ent_hex.bind(
                sequence=sequence,
                func=lambda _: self.sync_color_values('hex'),
                add='+'
            )
            for sb in [sb_hue, sb_sat, sb_lum]:
                sb.bind(
                    sequence=sequence,
                    func=lambda _: self.sync_color_values('hsl'),
                    add='+'
                )
                sb.configure(command=lambda: self.sync_color_values('hsl'))
            for sb in [sb_red, sb_grn, sb_blu]:
                sb.bind(
                    sequence=sequence,
                    func=lambda _: self.sync_color_values('rgb'),
                    add='+'
                )
                sb.configure(command=lambda: self.sync_color_values('rgb'))

        return container

    def coords_from_color(self, h: int, s: int) -> tuple:
        """Get the coordinates on the color spectrum from the color value"""
        o = self.tk.call('tk', 'scaling') / 2 * 10
        return (h / 360) * self.spectrum_width - o, (1-(s / 100)) * self.spectrum_height - o

    def hsl_from_coords(self, x: int, y: int) -> tuple:
        """Get the color value from the mouse position in the color spectrum"""
        h = int(min(360, max(0, (360/self.spectrum_width) * x)))
        s = int(min(100, max(0, 100 - ((100/self.spectrum_height) * y))))
        l = 50
        return h, s, l

    # color events
    def sync_color_values(self, model: str, color=None, lum_only=False):
        """Callback for when a color value changes. A change in one
        value will automatically update the other values and indicator
        so that all color models remain in sync."""
        if not color:
            color = self.hex.get() if model == 'hex' else self.dec.get() if model == 'dec' else self.rdec.get() if model == 'rdec' else (self.red.get(), self.grn.get(), self.blu.get()) if model == 'rgb' else (self.hue.get(), self.sat.get(), self.lum.get()) if model == 'hsl' else None
        if self.blend_mode == 'subtractive' and model == 'rdec': color = blend_subtractive_rdec(color_to_model(color, model, 'rgb'))
        h, s, l = color_to_model(color, model, 'hsl')
        r, g, b = color_to_model(color, model, 'rgb')
        hx = color_to_model(color, model, 'hex')
        contrast = contrast_color(r, g, b)
        self.hue.set(h)
        self.sat.set(s)
        self.lum.set(l)
        self.red.set(r)
        self.grn.set(g)
        self.blu.set(b)
        self.hex.set(hx)
        self.dec.set(color_to_model(color, model, 'dec'))
        self.rdec.set(blend_subtractive_rdec((r, g, b)) if self.blend_mode == 'subtractive' else color_to_model(color, model, 'rdec'))
        # update the preview fields
        if self.blend_mode == 'alpha':
            self.preview.configure(bg=hx)
            self.preview_lbl.configure(bg=hx, fg=contrast)
        else:
            bl = 1 - l/100 if self.blend_mode == 'subtractive' else l/100
            self.checkerboard.itemconfigure('cb_dark', fill=lum_to_alpha((r,g,b), bl, 200))
            self.checkerboard.itemconfigure('cb_light', fill=lum_to_alpha((r,g,b), bl, 235))

        # Update instructions
        self.textvariable.set(f'Recommended blend mode:\nNo alpha (black BG): {'subtractive' if l < 50 else 'additive'}\nAlpha (transparent BG): alpha')

        # move luminance indicator to the new location
        x = int(l / 100 * self.spectrum_width) - \
            ((self.spectrum_point - 2)//2)
        self.luminance_scale.moveto('luminance-indicator', x, 1)

        if not lum_only:
            # update luminance indicator with new color
            width = self.spectrum_width
            for x, l in enumerate(range(0, width, self.spectrum_point)):
                self.luminance_scale.itemconfigure(f'color{x}', fill=hsl_to_hex(h, s, l/width*100))
            # move spectrum indicator to the new color location
            self.color_spectrum.moveto('spectrum-indicator', *self.coords_from_color(h, s))
            self.color_spectrum.itemconfigure('spectrum-indicator', outline=contrast)

    def on_press_swatch(self, event):
        """Update the widget colors when a color swatch is clicked."""
        color = self.nametowidget(event.widget).cget('background')
        self.hex.set(color)
        self.sync_color_values(model='hex', color=color)

    def on_spectrum_interaction(self, event):
        """Update the widget colors when the color spectrum canvas is pressed"""
        self.sync_color_values(
            model='hsl',
            color=self.hsl_from_coords(event.x, event.y)
        )

    def on_luminance_interaction(self, event):
        """Update the widget colors when the color luminance scale is pressed"""
        self.lum.set(max(0, min(100, int((event.x / self.spectrum_width) * 100))))
        self.sync_color_values(model='hsl', lum_only=True)

    def os_colorchooser(self, event=None):
        name = self.tabview.select()
        index = self.tabview.index(name)
        if index == 3:
            self.tabview.select(tab_id=0)
            rgb_color = colorchooser.askcolor(self.hex.get())[0]
            if rgb_color:
                self.sync_color_values(model='rgb', color=rgb_color)


class App(Tk):
    def __init__(self, title):
        super().__init__()
        self.title(title)
        self.iconbitmap(Path(__file__).parent / 'MM.ico')
        self.style = ttk.Style()
        # self.geometry(f'{size[0]}x{size[1]}')
        # self.minsize(size[0], size[1])
        # self.font = font.nametofont(self.style.lookup(self, 'font')).actual()

        self.tk.call('source', Path(__file__).parent / 'tkBreeze' / 'tkBreeze.tcl')

        self.instructions = StringVar()

        self.top = ttk.Frame(self)
        self.top.pack()
        middle = ttk.Frame(self)
        middle.pack(fill=X)
        bottom = ttk.Frame(self)
        bottom.pack(fill=X)

        self.color_chooser = ColorChooser(self.top, initialcolor=SAVED_COLOR, textvariable=self.instructions) # +padding
        self.color_chooser.pack(fill=BOTH, expand=YES)

        copy_button = ttk.Button(middle, text='Copy to Clipboard', command=self.on_copy_click)
        copy_button.pack(side=LEFT, padx=10, pady=10)

        self.blendmode = ttk.Combobox(
            middle,
            values=['alpha', 'alphaadditive', 'additive', 'subtractive']
        )
        self.blendmode.pack(side=RIGHT, padx=10, pady=10)
        self.blendmode.set(self.blendmode['values'][0])
        self.blendmode.bind('<<ComboboxSelected>>', self.switch_blendmode)
        blendmode_label = ttk.Label(
            middle,
            text='Blend mode'
        ).pack(side=RIGHT, padx=10, pady=10)

        instructions_label = ttk.Label(
            bottom,
            textvariable=self.instructions,
            justify=LEFT,
            wraplength=300
        )
        instructions_label.pack(side=LEFT, padx=10, pady=5)

        ToolTip(
            instructions_label,
            delay=0.5,
            follow=False,
            justify=LEFT,
            msg="alpha:\nWorks best with textures that have a transparent background (black backgrounds stay black). The chosen color will always appear correctly, but with bright colors (luminance 50+), the texture color blends through (e.g. with a bright red color a blue texture will become purple, a white texture will stay bright red).\n\nadditive:\nWorks best with textures that have a black background. When using textures with transparent backgrounds, the alpha channel will be inverted. Dark colors will blend with the background, resulting in low visibility (invisibility when the color is black).\n\nalphaadditive:\nWorks with any texture, but dark colors will blend with the background, resulting in low visibility (invisibility when the color is black).\n\nsubtractive:\nWorks best with textures that have a black background. When using textures with transparent backgrounds, the alpha channel will be inverted. Light colors will blend with the background, resulting in low visibility (invisibility when the color is white).",
            y_offset=-460,
            width=450
        )
        #b, msg='Hover info', delay=0,
        #parent_kwargs={'bg': 'black', 'padx': 5, 'pady': 5},
        #fg='#ffffff', bg='#1c1c1c', padx=10, pady=10)

        theme_option = ttk.LabelFrame(
            bottom,
            text='Select theme',
            padding=(5, 0)
        )
        theme_option.pack(side=RIGHT, padx=10, pady=10)
        radio_1 = ttk.Radiobutton(
            theme_option,
            command=lambda: self.switch_theme('dark'),
            text='Dark',
            value=1
        )
        radio_1.grid(row=0, column=0, padx=2, sticky=NSEW)
        radio_2 = ttk.Radiobutton(
            theme_option,
            command=lambda: self.switch_theme('light'),
            text='Light',
            value=2
        )
        radio_2.grid(row=0, column=1, padx=2, sticky=NSEW)
        radio_1.invoke()

    def switch_theme(self, theme: str):
        self.tk.call('set_theme', theme)
        self.style.configure('custom.TFrame', background = 'indianred')
        # self.style.configure('bold.TLabel', font = (self.font['family'], self.font['size'], 'bold', self.font['slant']))

    def switch_blendmode(self, event):
        SAVED_COLOR = self.color_chooser.hex.get()
        self.color_chooser.destroy()
        self.color_chooser = ColorChooser(self.top, initialcolor=SAVED_COLOR, blend_mode=self.blendmode.selection_get(), textvariable=self.instructions)
        self.color_chooser.pack(side=TOP, fill=BOTH, expand=YES)

    def on_copy_click(self):
        self.clipboard_clear()
        self.clipboard_append(self.color_chooser.rdec.get())
        self.update()
        messagebox.showinfo('Copy Success', 'BGR Decimal Value copied to clipboard!')

if __name__ == '__main__':
    app = App('Decimal BGR Color Picker')
    app.mainloop()


"""Theme options:
change to
self.tk.call('source', './Azure/azure.tcl')


remove self.tk.call and radio buttons (default ttk which is Win11 window wrapper)


https://github.com/TomSchimansky/CustomTkinter/blob/master/examples/complex_example.py
import customtkinter as tk

# tk.set_appearance_mode('System') > default, not needed
# tk.set_default_color_theme('green')
# root = tk.CTk()


# https://ttkthemes.readthedocs.io/en/latest/themes.html
# from ttkthemes import ThemedTK

# root = ThemedTK()
# style = ttk.Style(root)
# style.theme_use('default')
"""

