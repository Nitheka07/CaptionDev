class TextToAssGenerator:
    def __init__(self, word_segments, style='typewriter', position='middle', font_name='Arial', hl_enable=True, custom_color='#00ffff', bg_enable=True, bg_color='#000000', bg_opacity=50):
        self.word_segments = word_segments
        self.style = style
        self.position = position
        self.font_name = font_name
        self.hl_enable = hl_enable
        self.custom_color = custom_color
        self.bg_enable = bg_enable
        self.bg_color = bg_color
        self.bg_opacity = bg_opacity
        
        # Position mapping to ASS alignment codes
        self.pos_codes = {
            'top': 8,
            'middle': 5,
            'bottom': 2
        }
        
    def get_header(self):
        border_style = 3 if self.bg_enable else 1
        
        # Convert bg_opacity (0-100) to ASS Alpha (00-FF). 
        # ASS Alpha: 00 is opaque, FF is transparent.
        alpha_val = int((1.0 - (self.bg_opacity / 100.0)) * 255)
        alpha_hex = hex(alpha_val)[2:].upper().zfill(2)
        
        ass_bg = self.hex_to_ass_color(self.bg_color, custom_alpha=alpha_hex)
        
        return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font_name},70,&H00FFFFFF&,&H000000FF&,&H00000000&,{ass_bg},-1,0,0,0,100,100,0,0,{border_style},6,3,2,10,10,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def hex_to_ass_color(self, hex_str, transparent_overlay=False, custom_alpha="00"):
        # Hex string comes as #RRGGBB (e.g. #FF5733)
        hex_str = hex_str.strip('#')
        r = hex_str[0:2]
        g = hex_str[2:4]
        b = hex_str[4:6]
        
        # ASS needs &HAABBGGRR& formatting. Default opaque alpha is 00.
        alpha = "88" if transparent_overlay else custom_alpha
        return f"&H{alpha}{b}{g}{r}&"

    def format_time(self, seconds):
        h = int(seconds / 3600)
        m = int((seconds % 3600) / 60)
        s = int(seconds % 60)
        cs = int((seconds * 100) % 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def group_words_into_lines(self, max_words=5, max_pause=1.0):
        lines = []
        current_line = []
        
        for w in self.word_segments:
            if current_line:
                last_word = current_line[-1]
                if len(current_line) >= max_words or (w['start'] - last_word['end']) > max_pause:
                    lines.append(current_line)
                    current_line = []
            current_line.append(w)
            
        if current_line:
            lines.append(current_line)
            
        return lines

    def generate_ass(self, output_path):
        lines = self.group_words_into_lines()
        ass_content = self.get_header()
        pos_tag = f"{{\\an{self.pos_codes.get(self.position, 5)}}}"
        
        ass_color = self.hex_to_ass_color(self.custom_color)
        
        # Color palettes definitions
        base_col = "&H00FFFFFF&" # Base white
        high_col = ass_color if self.hl_enable else base_col     # Set active color

        for line in lines:
            if not line:
                continue
                
            line_start = self.format_time(line[0]['start'])
            line_end = self.format_time(line[-1]['end'])
            
            # Setup dual-layer geometry dynamically based on background options
            if self.bg_enable:
                # Ghost Layer 0 purely provides the continuous background rectangle
                box_str = f"{pos_tag}{{\\1a&HFF&}}" + " ".join([w['word'].strip() for w in line])
                ass_content += f"Dialogue: 0,{line_start},{line_end},Default,,0,0,0,,{box_str.strip()}\n"
                
                # Active text Layer 1 clears its box outlines to avoid overlap
                base_hide_box = f"{{\\4a&HFF&}}{{\\3a&HFF&}}"
            else:
                base_hide_box = ""
                
            if self.style == 'normal':
                # Normal subtitle: just single static rendering over the full line
                text_str = f"{pos_tag}{base_hide_box}{{\\c{high_col}}}" + " ".join([w['word'].strip() for w in line])
                ass_content += f"Dialogue: 1,{line_start},{line_end},Default,,0,0,0,,{text_str.strip()}\n"
            else:
                # Typewriter: progressive reveal.
                # All past words are white, active word is colored (if enabled), future words are 100% invisible!
                # Future words must hide fill + outline + shadow, otherwise outlines can appear early.
                visible_word_tag = "{\\1a&H00&}" if self.bg_enable else "{\\1a&H00&}{\\3a&H00&}{\\4a&H00&}"
                hidden_word_tag = "{\\1a&HFF&}{\\3a&HFF&}{\\4a&HFF&}"
                for i, active_word in enumerate(line):
                    start_time = self.format_time(active_word['start'])
                    if i < len(line) - 1:
                        end_time = self.format_time(line[i+1]['start'])
                    else:
                        end_time = line_end
                    
                    text_str = f"{pos_tag}{base_hide_box}"
                    for w in line:
                        stripped = w['word'].strip()
                        if w['start'] < active_word['start']:
                            text_str += f"{visible_word_tag}{{\\c{base_col}}}{stripped} "
                        elif w['start'] == active_word['start']:
                            text_str += f"{visible_word_tag}{{\\c{high_col}}}{stripped} "
                        else:
                            text_str += f"{hidden_word_tag}{stripped} "
                            
                    ass_content += f"Dialogue: 1,{start_time},{end_time},Default,,0,0,0,,{text_str.strip()}\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
