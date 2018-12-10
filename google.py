#-*- coding:utf-8 -*-
from googletrans import Translator
import sys

reload(sys)
sys.setdefaultencoding( "utf-8" )

translator = Translator()
print translator.translate('今天天气不错').text
print translator.translate('今天天气不错', dest='ja').text
print translator.translate('今天天气不错', dest='ko').text