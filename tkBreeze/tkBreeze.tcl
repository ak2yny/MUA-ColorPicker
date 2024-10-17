source [file join [file dirname [info script]] theme breeze.tcl]
source [file join [file dirname [info script]] theme breeze-dark.tcl]

option add *tearOff 0

proc set_theme {mode} {
    if {$mode == "dark"} {
        ttk::style theme use "breeze-dark"
        tk_setPalette background [ttk::style lookup . -background]
    } elseif {$mode == "light"} {
        ttk::style theme use "breeze"
        tk_setPalette background [ttk::style lookup . -background]
    }
}
