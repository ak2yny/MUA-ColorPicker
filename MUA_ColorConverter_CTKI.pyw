from tkinter import *
from tkinter import colorchooser, messagebox
from customtkinter import *
from colorsys import rgb_to_hls, hls_to_rgb
from pathlib import Path
import darkdetect, sys, time

TRANSPARENT = 'systemTransparent' if sys.platform.startswith('darwin') else '#010203' # or '#000001'
if sys.platform.startswith('win'):
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2)
    SCALE_FACTOR = windll.shcore.GetScaleFactorForDevice(0) / 100
else:
    SCALE_FACTOR = 1

set_default_color_theme('green')


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
    decimal_value = (r << 16) | (g << 8) | b
    return decimal_value

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


class DecimalColorEntry(CTkEntry):
    '''A Entry widget that only accepts digits'''
    def __init__(self, master=None, textvariable=None, justify=None, **kwargs):
        self.justify = justify if justify else RIGHT
        textvariable.trace_add('write', self.validate)
        CTkEntry.__init__(self, master, textvariable=textvariable, justify=self.justify, **kwargs)
        self.get, self.set = textvariable.get, textvariable.set
    def validate(self, *args):
        value = self.get()
        if value and (not value.isdigit() or int(value) > 16777215):
            self.set(16777215) # hash(value)[-8:]

class CTkSpinbox(CTkFrame):
    """https://github.com/TomSchimansky/CustomTkinter/wiki/Create-new-widgets-(Spinbox)"""
    def __init__(self, *args,
                 width: int = 100,
                 height: int = 32,
                 step_size: int = 1,
                 from_: int = 0,
                 to: int = 2147483647,
                 textvariable: str = None,
                 command: callable = None,
                 **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.step_size = step_size
        self.from_=from_
        self.to=to
        self.command=command
        self.value=textvariable

        self.configure(fg_color=('gray78', 'gray28'))  # set frame color
        self.value.trace_add('write', self.value_validation)
        self.hold = None

        self.grid_columnconfigure((0, 2), weight=0)  # buttons don't expand
        self.grid_columnconfigure(1, weight=1)  # entry expands

        # hold not supported, but is in Button: repeatdelay=50, repeatinterval=50, command=self.subtract_button_callback
        self.subtract_button = CTkButton(self, text='-', width=height-6, height=height-6)
        self.subtract_button.grid(row=0, column=0, padx=(3, 0), pady=3)
        self.subtract_button.bind('<ButtonPress-1>', lambda _: self.subtract_button_callback())
        self.subtract_button.bind('<ButtonRelease-1>', lambda _: self.button_release())

        self.entry = CTkEntry(self, width=width-(2*height), height=height-6, border_width=0, justify=RIGHT, textvariable=self.value)
        self.entry.grid(row=0, column=1, columnspan=1, padx=3, pady=3, sticky=EW)
        for sequence in ['<Return>', '<KP_Enter>']:
            self.entry.bind(
                sequence=sequence,
                command=self.enter_value_callback,
                add='+'
            )

        self.add_button = CTkButton(self, text='+', width=height-6, height=height-6)
        self.add_button.grid(row=0, column=2, padx=(0, 3), pady=3)
        self.add_button.bind('<ButtonPress-1>', lambda _: self.add_button_callback())
        self.add_button.bind('<ButtonRelease-1>', lambda _: self.button_release())

    def add_button_callback(self):
        try:
            self.add_button_hold()
        except ValueError:
            self.after_cancel(self.hold)
            return

    def add_button_hold(self, speed=200):
        self.value.set(min(int(self.value.get()) + self.step_size, self.to))
        self.enter_value_callback()
        self.hold = self.after(max(30, speed - 20), self.add_button_hold, speed - 20)

    def subtract_button_callback(self, event=None):
        try:
            self.subtract_button_hold()
        except ValueError:
            self.after_cancel(self.hold)
            return

    def subtract_button_hold(self, speed=200):
        self.value.set(max(int(self.value.get()) - self.step_size, self.from_))
        self.enter_value_callback()
        self.hold = self.after(max(30, speed - 20), self.subtract_button_hold, speed - 20)

    def button_release(self):
        self.after_cancel(self.hold)

    def enter_value_callback(self, event=None):
        if self.command is not None:
            self.command()

    def value_validation(self, *args):
        value = self.value.get()
        try:
            self.value.set(max(min(int(value), self.to), self.from_))
        except:
            self.value.set(value if value == '' else str(self.from_))

    def get(self) -> int:
        try:
            return int(self.entry.get())
        except ValueError:
            return None

    def set(self, value: int):
        self.entry.delete(0, 'end')
        self.entry.insert(0, str(int(value)))

class CTkToolTip(Toplevel):
    """
    https://github.com/Akascape/CTkToolTip
    Creates a ToolTip (pop-up) widget for customtkinter.
    """

    def __init__(
            self,
            widget: any = None,
            message: str = None,
            delay: float = 0.2,
            follow: bool = True,
            x_offset: int = +20,
            y_offset: int = +10,
            bg_color: str = None,
            corner_radius: int = 10,
            border_width: int = 0,
            border_color: str = None,
            alpha: float = 0.95,
            padding: tuple = (10, 2),
            **message_kwargs):

        super().__init__()

        self.widget = widget

        self.withdraw()

        # Disable ToolTip's title bar
        self.overrideredirect(True)
        self.bg_color = bg_color or ThemeManager.theme['CTkFrame']['fg_color']

        if sys.platform.startswith('win'):
            self.attributes('-transparentcolor', TRANSPARENT)
            self.transient()
        elif sys.platform.startswith('darwin'):
            self.attributes('-transparent', True)
            self.transient(self.master)
        else:
            corner_radius = 0
            self.transient()

        self.resizable(width=True, height=True)

        # Make the background transparent
        self.config(background=TRANSPARENT)

        # StringVar instance for msg string
        self.messageVar = StringVar()
        self.message = message
        self.messageVar.set(self.message)

        self.delay = delay
        self.follow = follow
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.corner_radius = corner_radius
        self.alpha = alpha
        self.border_width = border_width
        self.padding = padding
        self.tl_color = ThemeManager.theme['CTkToplevel']['fg_color']
        self.border_color = border_color
        self.disable = False

        # visibility status of the ToolTip inside|outside|visible
        self.status = 'outside'
        self.last_moved = 0
        self.attributes('-alpha', self.alpha)

        # Add the message widget inside the tooltip
        self.transparent_frame = Frame(self, bg=TRANSPARENT)
        self.transparent_frame.pack(padx=0, pady=0, fill=BOTH, expand=True)

        self.frame = CTkFrame(self.transparent_frame,
                              bg_color=TRANSPARENT,
                              corner_radius=self.corner_radius,
                              border_width=self.border_width,
                              fg_color=self.bg_color,
                              border_color=self.border_color)
        self.frame.pack(padx=0, pady=0, fill=BOTH, expand=True)

        self.message_label = CTkLabel(self.frame, textvariable=self.messageVar, **message_kwargs)
        self.message_label.pack(fill=BOTH, padx=self.padding[0] + self.border_width,
                                pady=self.padding[1] + self.border_width, expand=True)

        # Add bindings to the widget without overriding the existing ones
        self.widget.bind('<Enter>', self.on_enter, add='+')
        self.widget.bind('<Leave>', self.on_leave, add='+')
        self.widget.bind('<Motion>', self.on_enter, add='+')
        self.widget.bind('<B1-Motion>', self.on_enter, add='+')
        self.widget.bind('<Destroy>', lambda _: self.hide(), add='+')

    def show(self) -> None:
        """
        Enable the widget.
        """
        self.disable = False

    def on_enter(self, event) -> None:
        """
        Processes motion within the widget including entering and moving.
        """

        if self.disable:
            return
        self.last_moved = time.time()

        # Set the status as inside for the very first time
        if self.status == 'outside':
            self.status = 'inside'

        # If the follow flag is not set, motion within the widget will make the ToolTip dissapear
        if not self.follow:
            self.status = 'inside'
            self.withdraw()

        # Calculate available space on the right side of the widget relative to the screen
        root_width = self.winfo_screenwidth()
        widget_x = event.x_root
        space_on_right = root_width - widget_x

        # Calculate the width of the tooltip's text based on the length of the message string
        text_width = self.message_label.winfo_reqwidth()

        # Calculate the offset based on available space and text width to avoid going off-screen on the right side
        offset_x = self.x_offset
        if space_on_right < text_width + 20:  # Adjust the threshold as needed
            offset_x = -text_width - 20  # Negative offset when space is limited on the right side

        # Offsets the ToolTip using the coordinates od an event as an origin
        self.geometry(f'+{event.x_root + offset_x}+{event.y_root + self.y_offset}')

        # Time is in integer: milliseconds
        self.after(int(self.delay * 1000), self._show)

    def on_leave(self, event=None) -> None:
        """
        Hides the ToolTip temporarily.
        """

        if self.disable: return
        self.status = 'outside'
        self.withdraw()

    def _show(self) -> None:
        """
        Displays the ToolTip.
        """

        if not self.widget.winfo_exists():
            self.hide()
            self.destroy()

        if self.status == 'inside' and time.time() - self.last_moved >= self.delay:
            self.status = 'visible'
            self.deiconify()

    def hide(self) -> None:
        """
        Disable the widget from appearing.
        """
        if not self.winfo_exists():
            return
        self.withdraw()
        self.disable = True

    def is_disabled(self) -> None:
        """
        Return the window state
        """
        return self.disable

    def get(self) -> None:
        """
        Returns the text on the tooltip.
        """
        return self.messageVar.get()

    def configure(self, message: str = None, delay: float = None, bg_color: str = None, **kwargs):
        """
        Set new message or configure the label parameters.
        """
        if delay: self.delay = delay
        if bg_color: self.frame.configure(fg_color=bg_color)

        self.messageVar.set(message)
        self.message_label.configure(**kwargs)

# color picker by TtkBootstrap
# https://github.com/israel-dryer/ttkbootstrap/tree/master
class ColorChooser(CTkFrame):
    """A class which creates a color chooser widget
    
    ![](../../assets/dialogs/querybox-get-color.png)    
    """

    def __init__(self, master, initialcolor=None, blend_mode=None, textvariable=None):
        super().__init__(master)
        self.initialcolor = color_to_hex(self, initialcolor) if initialcolor else master['bg']
        self.blend_mode = blend_mode or 'alpha'
        self.textvariable = textvariable

        self.tframe = CTkFrame(self)
        self.tframe.pack(fill=X)
        self.bframe = CTkFrame(self)
        self.bframe.pack(fill=X)

        self.tabview = CTkTabview(self.tframe, anchor=NW)
        self.tabview.pack(fill=BOTH)
        self.tabview.add('Advanced')
        self.tabview.add('Standard')
        self.tabview.add('Outsider')
        self.tabview.add('More...')
        self.bg_color = self.tabview.cget('fg_color')
        self.tframe.configure(fg_color=self.bg_color)
        self.bframe.configure(fg_color=self.bg_color)

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
        self.tab_height = 240
        self.tab_width = 440
        self.spectrum_height = int(self.tab_height * SCALE_FACTOR)
        self.spectrum_width = int(self.tab_width * SCALE_FACTOR)
        self.spectrum_point = 12

        # build widgets
        spectrum_frame = CTkFrame(self.tabview.tab('Advanced'))
        spectrum_frame.grid()
        self.color_spectrum = self.create_spectrum(spectrum_frame)
        self.color_spectrum.pack(fill=X, expand=YES, side=TOP)
        self.standard_swatches = self.create_swatches(
            self.tabview.tab('Standard'), STD_COLORS).grid()
        self.outsider_swatches = self.create_swatches_ns(
            self.tabview.tab('Outsider'), OUTSIDERS_COLORS).grid()
        self.more = CTkFrame(self.tabview.tab('More...'))
        self.tabview.configure(command=self.os_colorchooser)
        self.luminance_scale = self.create_luminance_scale(self.tframe)
        self.luminance_scale.pack(fill=X, padx=8, pady=(0, 8))

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
        canvas = Canvas(master, width=width, height=height, highlightbackground=self.bg_color[1], background=self.bg_color[1], cursor='tcross')
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
        s = int(10 * SCALE_FACTOR)
        width = int(3 * SCALE_FACTOR)
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
        boxwidth = self.tab_width / len(STD_COLORS) - boxpadx * 2
        boxheight = self.tab_height / (len(STD_SHADES) + 1) - boxpady * 2
        container = CTkFrame(master)

        # themed colors - regular colors
        for row in color_rows:
            rowframe = CTkFrame(container, fg_color=self.bg_color)
            for color in row:
                swatch = CTkFrame(
                    master=rowframe,
                    fg_color=color,
                    width=boxwidth,
                    height=boxheight
                ) # autostyle=False
                swatch.bind('<Button-1>', self.on_press_swatch)
                swatch.pack(side=LEFT, padx=boxpadx, pady=boxpady)
            rowframe.pack(fill=X, expand=YES)

        return container

    def create_luminance_scale(self, master):
        """Create the color luminance canvas"""
        # widget dimensions
        xf = self.spectrum_point
        height = xf * SCALE_FACTOR
        width = self.spectrum_width

        canvas = Canvas(master, height=height, width=width, highlightbackground=self.bg_color[1], background=self.bg_color[1])

        # add interactions to scale
        for x, l in enumerate(range(0, width, xf)):
            canvas.create_rectangle(x*xf, 0, (x*xf)+xf, height, width=0, tags=[f'color{x}'])
            canvas.bind('<B1-Motion>', self.on_luminance_interaction, add='+')
            canvas.bind('<Button-1>', self.on_luminance_interaction, add='+')
        return canvas

    def create_luminance_indicator(self):
        """Create an indicator that will move in the position of the luminance value"""
        xf = self.spectrum_point * SCALE_FACTOR
        x1 = int(0.5 * self.spectrum_width) - \
            ((xf - 2)//2)
        tag = 'luminance-indicator'
        self.luminance_scale.create_rectangle(
            x1, 0, x1 + xf, xf - 3,
            fill='white',
            outline='black',
            tags=[tag]
        )
        self.luminance_scale.tag_raise(tag)

    def create_preview(self, master):
        """Create a preview and decimals"""
        container = CTkFrame(master=master, fg_color=self.bg_color)

        # the frame and label for the new color
        if self.blend_mode == 'alpha':
            self.preview = CTkFrame(
                master=container,
                bg_color=self.bg_color,
                border_width=2
            )
            self.preview.pack(side=TOP, fill=BOTH, expand=YES, padx=(5, 0))
            self.preview_lbl = CTkLabel(
                master=self.preview,
                text='Preview',
                width=7
            )
            self.preview_lbl.pack(anchor=N, pady=5)
        else:
            cb_preview = CTkFrame(
                master=container,
                bg_color=self.bg_color
            )
            cb_preview.pack(side=TOP, fill=BOTH, expand=YES, padx=(6, 0))
            s = int(20 * SCALE_FACTOR)
            d = int(240 * SCALE_FACTOR)
            self.checkerboard = Canvas(
                cb_preview,
                highlightbackground=self.bg_color[0],
                width=d,
                height=d
            )
            for xi, x in enumerate(range(0, d, s)):
                for yi, y in enumerate(range(0, d, s)):
                    self.checkerboard.create_rectangle(x, y, x+s, y+s, width=0, tags=['cb_light' if (xi + yi) % 2 else 'cb_dark'])
            self.checkerboard.place(relwidth=1, relheight=1)

            if sys.platform.startswith('win'):
                cb_border = CTkFrame(cb_preview, border_width=3, fg_color=TRANSPARENT)
                cb_border.place(relwidth=1, relheight=1)
                hwnd = cb_border.winfo_id()
                new_exstyle = windll.user32.GetWindowLongA(hwnd, -20) | 0x00080000  # WS_EX_LAYERED
                windll.user32.SetWindowLongA(hwnd, -20, new_exstyle)  # GWL_EXSTYLE
                windll.user32.SetLayeredWindowAttributes(hwnd, int(TRANSPARENT[-2:] + TRANSPARENT[-4:-2] + TRANSPARENT[-6:-4], 16), 255, 0x00000001)  # LWA_COLORKEY = 0x00000001

        # Decimal fields
        decimals = CTkFrame(master=container, bg_color=self.bg_color, fg_color=self.bg_color)
        decimals.pack(anchor=SE, padx=(2, 0))
        ent_dec = DecimalColorEntry(decimals, width=80, textvariable=self.dec)
        ent_dec.grid(row=0, column=1, padx=2, pady=2, sticky=EW)
        ent_rdec = DecimalColorEntry(decimals, width=80, textvariable=self.rdec, border_width=3, border_color='indianred')
        ent_rdec.grid(row=1, column=1, padx=2, pady=2, sticky=EW)
        
        lbl_cnf = {'master': decimals, 'anchor': E}
        CTkLabel(**lbl_cnf, text='Decimal RGB').grid(row=0, column=0, sticky=E)
        CTkLabel(**lbl_cnf, text='Decimal BGR', font=CTkFont(weight='bold')).grid(row=1, column=0, sticky=E)
        for sequence in ['<Return>', '<KP_Enter>']:
            ent_dec.bind(
                sequence=sequence,
                command=lambda _: self.sync_color_values('dec'),
                add='+'
            )
            ent_rdec.bind(
                sequence=sequence,
                command=lambda _: self.sync_color_values('rdec'),
                add='+'
            )
        self.update()
        if self.blend_mode != 'alpha': cb_preview.configure(height=decimals.winfo_height() / SCALE_FACTOR, width=decimals.winfo_width() / SCALE_FACTOR)

        return container

    def create_value_inputs(self, master):
        """Create color value input widgets"""
        container = CTkFrame(master=master, fg_color=self.bg_color)
        for x in range(4):
            container.columnconfigure(x, weight=1)

        # value labels
        lbl_cnf = {'master': container, 'anchor': E}
        CTkLabel(**lbl_cnf, text='Hue').grid(row=0, column=0, sticky=E)
        CTkLabel(**lbl_cnf, text='Sat').grid(row=1, column=0, sticky=E)
        CTkLabel(**lbl_cnf, text='Lum').grid(row=2, column=0, sticky=E)
        CTkLabel(**lbl_cnf, text='Hex').grid(row=3, column=0, sticky=E)
        CTkLabel(**lbl_cnf, text='Red').grid(row=0, column=2, sticky=E)
        CTkLabel(**lbl_cnf, text='Green').grid(row=1, column=2, sticky=E)
        CTkLabel(**lbl_cnf, text='Blue').grid(row=2, column=2, sticky=E)

        # value spinners and entry widgets
        rgb_cnf = {'master': container, 'from_': 0, 'to': 255, 'width': 100, 'command': lambda: self.sync_color_values('rgb')}
        sl_cnf = {'master': container, 'from_': 0, 'to': 100, 'width': 100, 'command': lambda: self.sync_color_values('hsl')}
        hue_cnf = {'master': container, 'from_': 0, 'to': 360, 'width': 100, 'command': lambda: self.sync_color_values('hsl')}
        sb_hue = CTkSpinbox(**hue_cnf, textvariable=self.hue)
        sb_hue.grid(row=0, column=1, padx=4, pady=2, sticky=EW)
        sb_sat = CTkSpinbox(**sl_cnf, textvariable=self.sat)
        sb_sat.grid(row=1, column=1, padx=4, pady=2, sticky=EW)
        sb_lum = CTkSpinbox(**sl_cnf, textvariable=self.lum)
        sb_lum.grid(row=2, column=1, padx=4, pady=2, sticky=EW)
        sb_red = CTkSpinbox(**rgb_cnf, textvariable=self.red)
        sb_red.grid(row=0, column=3, padx=4, pady=2, sticky=EW)
        sb_grn = CTkSpinbox(**rgb_cnf, textvariable=self.grn)
        sb_grn.grid(row=1, column=3, padx=4, pady=2, sticky=EW)
        sb_blu = CTkSpinbox(**rgb_cnf, textvariable=self.blu)
        sb_blu.grid(row=2, column=3, padx=4, pady=2, sticky=EW)
        ent_hex = CTkEntry(container, textvariable=self.hex)
        ent_hex.grid(row=3, column=1, padx=4, columnspan=3, pady=2, sticky=EW)

        # event binding for updating colors on value change
        for sequence in ['<Return>', '<KP_Enter>']:
            ent_hex.bind(
                sequence=sequence,
                command=lambda _: self.sync_color_values('hex'),
                add='+'
            )

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
            self.preview.configure(fg_color=hx)
            self.preview_lbl.configure(fg_color=hx, text_color=contrast)
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
        color = self.nametowidget(event.widget).master.cget('fg_color')
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
        name = self.tabview.get()
        if name == 'More...':
            self.tabview.set('Advanced')
            rgb_color = colorchooser.askcolor(self.hex.get())[0]
            if rgb_color:
                self.sync_color_values(model='rgb', color=rgb_color)


class App(CTk):
    def __init__(self, title):
        super().__init__()
        self.title(title)
        self.iconbitmap(Path(__file__).parent / 'MM.ico')
        # self.geometry(f'{size[0]}x{size[1]}')
        # self.minsize(size[0], size[1])

        self.instructions = StringVar()

        self.top = CTkFrame(self, fg_color='transparent')
        self.top.pack()
        middle = CTkFrame(self, corner_radius=0)
        middle.pack(fill=X)
        bottom = CTkFrame(self, corner_radius=0)
        bottom.pack(fill=X)

        self.color_chooser = ColorChooser(self.top, initialcolor=SAVED_COLOR, textvariable=self.instructions)
        self.color_chooser.pack(fill=BOTH, expand=YES)

        copy_button = CTkButton(middle, text='Copy to Clipboard', command=self.on_copy_click)
        copy_button.pack(side=LEFT, padx=10, pady=10)

        blendmode = CTkOptionMenu(
            middle,
            values=['alpha', 'alphaadditive', 'additive', 'subtractive'],
            command=self.switch_blendmode
        ).pack(side=RIGHT, padx=10, pady=10)
        blendmode_label = CTkLabel(
            middle,
            text='Change blend mode'
        ).pack(side=RIGHT, padx=10, pady=10)

        instructions_label = CTkLabel(
            bottom,
            textvariable=self.instructions,
            font=CTkFont(size=11),
            justify=LEFT,
            wraplength=160
        )
        instructions_label.pack(side=LEFT, padx=10, pady=5)

        instructions_tt = CTkToolTip(
            instructions_label,
            follow=False,
            justify=LEFT,
            message="alpha:\nWorks best with textures that have a transparent background (black backgrounds stay black). The chosen color will always appear correctly, but with bright colors (luminance 50+), the texture color blends through (e.g. with a bright red color a blue texture will become purple, a white texture will stay bright red).\n\nadditive:\nWorks best with textures that have a black background. When using textures with transparent backgrounds, the alpha channel will be inverted. Dark colors will blend with the background, resulting in low visibility (invisibility when the color is black).\n\nalphaadditive:\nWorks with any texture, but dark colors will blend with the background, resulting in low visibility (invisibility when the color is black).\n\nsubtractive:\nWorks best with textures that have a black background. When using textures with transparent backgrounds, the alpha channel will be inverted. Light colors will blend with the background, resulting in low visibility (invisibility when the color is white).",
            y_offset=-430,
            wraplength=430
        )

        theme_option = CTkOptionMenu(
            bottom,
            values=['System', 'Light', 'Dark'],
            command=self.switch_theme
        ).pack(side=RIGHT, padx=10, pady=10)
        theme_label = CTkLabel(
            bottom,
            text='Change theme'
        ).pack(side=RIGHT, padx=10, pady=10)

        self.current_theme = 'System'
        self.fix_theme(self.current_theme)

    def switch_theme(self, theme: str):
        self.current_theme = theme
        set_appearance_mode(theme) # Modes: 'System' (standard), 'Dark', 'Light'
        self.fix_theme(theme)

    def fix_theme(self, theme: str):
        if theme == 'System': theme = darkdetect.theme()
        c = self.color_chooser.tabview.cget('fg_color')[1 if theme == 'Dark' else 0]
        self.color_chooser.color_spectrum.configure(highlightbackground=c, background=c)
        self.color_chooser.luminance_scale.configure(highlightbackground=c, background=c)

    def switch_blendmode(self, blend_mode: str):
        SAVED_COLOR = self.color_chooser.hex.get()
        self.color_chooser.destroy()
        self.color_chooser = ColorChooser(self.top, initialcolor=SAVED_COLOR, blend_mode=blend_mode, textvariable=self.instructions)
        self.color_chooser.pack(side=TOP, fill=BOTH, expand=YES)
        self.fix_theme(self.current_theme)

    def on_copy_click(self):
        self.clipboard_clear()
        self.clipboard_append(self.color_chooser.rdec.get())
        self.update()
        messagebox.showinfo('Copy Success', 'BGR Decimal Value copied to clipboard!')

if __name__ == '__main__':
    app = App('Decimal BGR Color Picker')
    app.mainloop()

"""
class App(CTkFrame):
    def __init__(self, master, change_colors):
        super().__init__(master=master)
        self.color_option = CTkOptionMenu(
            middle,
            width=120,
            values=['green', 'blue', 'dark-blue'],
            command=change_colors
        )
        self.color_option.pack(side=RIGHT, padx=10, pady=10)

class AppWrapper(CTk):
    def __init__(self, title):
        super().__init__()
        self.title(title)
        self.iconbitmap('./MM.ico')

        self.app = App(self, self.change_colors)
        self.app.pack(expand=True, fill=BOTH)

    def change_colors(self, theme: str):
        set_default_color_theme(theme)
        global SAVED_COLOR
        SAVED_COLOR = self.app.color_chooser.hex.get()
        self.app.destroy()
        self.app = App(self, self.change_colors)
        self.app.pack(expand=True, fill=BOTH)

if __name__ == '__main__':
    appw = AppWrapper('RGB to Decimal BGR Color Picker')
    appw.mainloop()
"""