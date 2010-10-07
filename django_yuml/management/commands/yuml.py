from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.db.models.loading import get_models, get_apps, get_app
from django.core.exceptions import ImproperlyConfigured
import os

class Command(BaseCommand):
  option_list = BaseCommand.option_list + (
    make_option('--all-applications', '-a', action='store_true', dest='all_applications',
      help='Automaticly include all applications from INSTALLED_APPS'),
    make_option('--output', '-o', action='store', dest='outputfile',
      help='Render output file. Type of output dependend on file extensions. Use png,jpg or pdf to render graph to image to.'),
    make_option('--scale', '-s', action='store', dest='scale',
      help='Set a scale percentage. Applies only for -o'),
    make_option('--scruffy','', action='store_true', dest='scruffy',
      help='Make a scuffy diagram')
  )
  args = '[appname appname]'
  help = 'Generating model class diagram for yuml.me'
  label = 'application name'
  
  yuml = ''
  YUMLME_URL="http://yuml.me/diagram/"
    
  def handle(self, *args, **options):
    if len(args) < 1 and not options['all_applications']:
      raise CommandError("need one or more arguments for appname")
    self.generate_yuml(args, **options)
    if options['outputfile']:
      self.render_to(**options)
    else:
      self.print_output()
  
  def render_to(self, **options):
    import urllib2,urllib
    filename = options['outputfile']
    extension = os.path.splitext(filename)[1]
    url_yuml = urllib.quote(self.yuml.strip().replace("\n",", "))

    if options['scale']:
      self.YUMLME_URL = self.YUMLME_URL + "scale:%s" % options['scale']
    if options['scruffy']:
      if self.YUMLME_URL[-1]!="/":
        self.YUMLME_URL += ";"
      self.YUMLME_URL = self.YUMLME_URL + "scruffy"
    
    try:
      if self.YUMLME_URL[-1]=="/":
        self.YUMLME_URL = self.YUMLME_URL[:-1]
      r = urllib2.urlopen("%s/class/%s%s" % (self.YUMLME_URL, url_yuml, extension))
    except urllib2.HTTPError, e:
      raise CommandError("Error occured while generating %s, %s" % (extension,e))
    
    resp = r.read()
    f = open(options['outputfile'],'w+')
    f.write(resp)
    f.close()
  
  def print_output(self):
    print self.yuml.encode('utf-8')
  
  def generate_yuml(self,app_labels,**options):
    imported_objects = {}        

    if not options['all_applications']:
      for application in app_labels:
        try:
          app_mod = get_app(application)
          app_models = get_models(app_mod)
          if not app_models:
            continue
          model_labels = ", ".join([model.__name__ for model in app_models])
          for model in app_models:
            try:
              imported_objects[model.__name__] = getattr(__import__(app_mod.__name__, {}, {}, model.__name__), model.__name__)
            except AttributeError, e:
              continue
        except ImproperlyConfigured, e:
          raise CommandError("Specified application not found: %s" % e)
    else:
      for app_mod in get_apps():
        app_models = get_models(app_mod)
        if not app_models:
          continue
        model_labels = ", ".join([model.__name__ for model in app_models])
        for model in app_models:
          try:
            imported_objects[model.__name__] = getattr(__import__(app_mod.__name__, {}, {}, model.__name__), model.__name__)
          except AttributeError, e:
            continue
    
    for model_name in imported_objects:
      model = imported_objects[model_name]
      self.yuml += "[%s|" % (model._meta.module_name)
      relations = {}
      for field in model._meta.fields:
        if field.__class__.__name__=='ForeignKey':
          relations[field.attname] = field.related.parent_model._meta.module_name
        self.yuml += "%s (%s);" % (field.attname, field.__class__.__name__)
      self.yuml += "]\n" 
      if len(relations)>0:
        for column in relations:
          self.yuml += "[%s]-%s>[%s]\n"% (model._meta.module_name,column,relations[column])