# Contains all the xpaths used by the webdriver to find the page components


# Qr code to scan
QR_CODE = "//canvas[@aria-label='Scan me!']"

# Home page logo after finishing loading
HOME_PAGE = '//div[@data-asset-intro-image-light="true"][@style="transform: scale(1); opacity: 1;"]'

# Search bar to search a contact
SEARCH_BAR = '//div[@contenteditable="true"][@data-tab="3"]'

# Contact box to click to open the chat with the given name
CONTACT_BOX = '//span[contains(@title,"{}")]'

# Input box to type the message
INPUT_BOX = '//div[@contenteditable="true"][@spellcheck="true"]'

# Bubble that indicated the number of unread messages
UNREAD_MESSAGES = '//span[contains(@aria-label,"unread message")]'

# Individual message box of the page
MESSAGES = '//div[contains(@class,"message-in focusable-list-item")][@tabindex="-1"]'

# Text inside a message box
TEXT_IN_MESSAGE = './/span[contains(@class,"selectable-text copyable-text")]'

# Audio inside a message box
AUDIO_IN_MESSAGE = ".//audio"

# Image inside a message box
IMAGE_IN_MESSAGE = './/img[contains(@src,"blob:")]'

# Finds the name of the user that sent a message from the unread bubble counter
WHO_FROM_UNREAD = "./../../../../../div[1]/div[1]"

# Sender inside a message box [Whatsapp groups only], to use with a different number
# of divs based on the message type
SENDER_IN_MESSAGE = ".{}/span"

# Div to use to find if the message is in a group
DIV = "/div[1]"

# Caption of an image
IMAGE_CAPTION = "./div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/span/span"

# Add file icon
ADD_FILE = '//span[@data-testid="{0}"][@data-icon="{0}"]'

# Clip to open the actions
CLIP = "clip"

# Attach image action inside the clip
ATTACH_IMAGE = "attach-image"

# Send button
SEND = "send"

# Javascript to extract an assets from the site
DOWNLOAD_BLOB_SCRIPT = """
var uri = arguments[0];
var callback = arguments[1];
var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),
t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)
i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);
for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],
a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];
return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):
t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),
new TextDecoder("ascii").decode(a)};
var xhr = new XMLHttpRequest();
xhr.responseType = 'arraybuffer';
xhr.onload = function(){ callback(toBase64(xhr.response)) };
xhr.onerror = function(){ callback(xhr.status) };
xhr.open('GET', uri);
xhr.send();"""
