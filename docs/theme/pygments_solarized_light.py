from pygments.style import Style
from pygments.token import (Keyword, Name, Comment, String, Error, Text, Number, Operator, Generic,
                            Whitespace, Other, Literal, Punctuation)


class LightStyle(Style):
    """
    The Solarized Light style
    """
    default_style = ""

    base03 = '#002b36'
    base02 = '#073642'
    base01 = '#586e75'  # emphasized content
    base00 = '#657b83'  # primary content
    base0 = '#839496'
    base1 = '#93a1a1'  # secondary content
    base2 = '#eee8d5'  # background highlights
    base3 = '#fdf6e3'  # background
    yellow = '#b58900'
    orange = '#cb4b16'
    red = '#dc322f'
    magenta = '#d33682'
    violet = '#6c71c4'
    blue = '#268bd2'
    cyan = '#2aa198'
    green = '#859900'

    background_color = base3
    pri = base00
    emph = base01
    sec = base1

    comment = 'italic ' + sec

    # @formatter:off
    styles = {
        Text:                   pri,                # class: ''
        Whitespace:             base3,              # class: 'w'
        Error:                  red,                # class: 'err'
        Other:                  pri,                # class: 'x'

        Comment:                comment,            # class: 'c'
        Comment.Multiline:      comment,            # class: 'cm'
        Comment.Preproc:        comment,            # class: 'cp'
        Comment.Single:         comment,            # class: 'c1'
        Comment.Special:        comment,            # class: 'cs'

        Keyword:                green,              # class: 'k'
        Keyword.Constant:       green,              # class: 'kc'
        Keyword.Declaration:    green,              # class: 'kd'
        Keyword.Namespace:      orange,             # class: 'kn'
        Keyword.Pseudo:         orange,             # class: 'kp'
        Keyword.Reserved:       green,              # class: 'kr'
        Keyword.Type:           green,              # class: 'kt'

        Operator:               pri,                # class: 'o'
        Operator.Word:          green,              # class: 'ow'

        Name:                   emph,               # class: 'n'
        Name.Attribute:         pri,                # class: 'na'
        Name.Builtin:           blue,               # class: 'nb'
        Name.Builtin.Pseudo:    blue,               # class: 'bp'
        Name.Class:             blue,               # class: 'nc'
        Name.Constant:          yellow,             # class: 'no'
        Name.Decorator:         orange,             # class: 'nd'
        Name.Entity:            orange,             # class: 'ni'
        Name.Exception:         orange,             # class: 'ne'
        Name.Function:          blue,               # class: 'nf'
        Name.Property:          blue,               # class: 'py'
        Name.Label:             pri,                # class: 'nc'
        Name.Namespace:         pri,                # class: 'nn'
        Name.Other:             pri,                # class: 'nx'
        Name.Tag:               green,              # class: 'nt'
        Name.Variable:          orange,             # class: 'nv'
        Name.Variable.Class:    blue,               # class: 'vc'
        Name.Variable.Global:   blue,               # class: 'vg'
        Name.Variable.Instance: blue,               # class: 'vi'

        Number:                 cyan,               # class: 'm'
        Number.Float:           cyan,               # class: 'mf'
        Number.Hex:             cyan,               # class: 'mh'
        Number.Integer:         cyan,               # class: 'mi'
        Number.Integer.Long:    cyan,               # class: 'il'
        Number.Oct:             cyan,               # class: 'mo'

        Literal:                pri,                # class: 'l'
        Literal.Date:           pri,                # class: 'ld'

        Punctuation:            pri,                # class: 'p'

        String:                 cyan,               # class: 's'
        String.Backtick:        cyan,               # class: 'sb'
        String.Char:            cyan,               # class: 'sc'
        String.Doc:             cyan,               # class: 'sd'
        String.Double:          cyan,               # class: 's2'
        String.Escape:          orange,             # class: 'se'
        String.Heredoc:         cyan,               # class: 'sh'
        String.Interpol:        orange,             # class: 'si'
        String.Other:           cyan,               # class: 'sx'
        String.Regex:           cyan,               # class: 'sr'
        String.Single:          cyan,               # class: 's1'
        String.Symbol:          cyan,               # class: 'ss'

        Generic:                pri,                # class: 'g'
        Generic.Deleted:        pri,                # class: 'gd'
        Generic.Emph:           pri,                # class: 'ge'
        Generic.Error:          pri,                # class: 'gr'
        Generic.Heading:        pri,                # class: 'gh'
        Generic.Inserted:       pri,                # class: 'gi'
        Generic.Output:         pri,                # class: 'go'
        Generic.Prompt:         pri,                # class: 'gp'
        Generic.Strong:         pri,                # class: 'gs'
        Generic.Subheading:     pri,                # class: 'gu'
        Generic.Traceback:      pri,                # class: 'gt'
    }
    # @formatter:on

