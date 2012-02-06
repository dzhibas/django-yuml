from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.db.models.loading import get_models, get_apps, get_app
from django.core.exceptions import ImproperlyConfigured


class YUMLFormatter(object):
    START      = '['
    END        = ']'
    PIPE       = '|'
    END_FIELD  = ';'
    START_TYPE = ': '
    END_TYPE   = ''
    INHERIT    = '^--'
    APP_MODEL  = '.'
    FAKE_FIELD = '...{bg:orange}'
    PK         = '(pk) '
    RELATION   = '%(card_from)s<-%(related)s%(symm)s%(card_to)s'
    THROUGH    = '<-.-%(related)s%(symm)s'

    @classmethod
    def wrap(kls, string):
        return kls.START + string + kls.END

    @classmethod
    def wrap_type(kls, string):
        return kls.START_TYPE + string + kls.END_TYPE

    @classmethod
    def wrap_field(kls, string):
        return string + kls.END_FIELD

    @classmethod
    def label(kls, model):
        return model._meta.app_label + kls.APP_MODEL + model._meta.object_name

    @classmethod
    def external(kls, model):
        return kls.wrap(kls.label(model) + kls.PIPE + kls.wrap_field(kls.FAKE_FIELD))

    @classmethod
    def inherit(kls, model, parent):
        return kls.wrap(kls.label(parent)) + kls.INHERIT + kls.wrap(kls.label(model))

    @classmethod
    def field(kls, field):
        '''TODO: null and default?'''
        string = ''
        if field.primary_key:
            string += kls.PK
        if field.rel:
            t = kls.label(field.rel.to)
        else:
            t = field.__class__.__name__
            t = t.replace('Field', '')
        string += field.name + kls.wrap_type(t)
        return kls.wrap_field(string)

    @classmethod
    def rel_arrow(kls, model, relation):
        '''TODO:
        cardinality symm and related
        '''
        d = {
            'card_from' :'',
            'related'   : relation.related_name or '',
            'card_to'   :'',
            'symm'      :'',
        }
        return kls.RELATION % d

    @classmethod
    def through_arrow(kls, model, relation):
        '''TODO:
        cardinality symm and related
        '''
        d = {
            'related'   : relation.related_name or '',
            'symm'      :'',
        }
        return kls.THROUGH % d

    @classmethod
    def relation(kls, model, relation):
        return kls.wrap(kls.label(relation.to)) + kls.rel_arrow(model, relation) + kls.wrap(kls.label(model))

    @classmethod
    def through(kls, model, relation):
        return kls.wrap(kls.label(relation.to)) + kls.through_arrow(model, relation) + kls.wrap(kls.label(model))


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--all-applications', '-a', action='store_true',
                    dest='all_applications',
                    help='Automaticly include all applications from\
                    INSTALLED_APPS'),
        make_option('--output', '-o', action='store', dest='outputfile',
                    help='Render output file. Type of output dependend\
                    on file extensions. Use png,jpg or pdf to render\
                    graph to image to.'),
        make_option('--scale', '-s', action='store', dest='scale',
                    help='Set a scale percentage. Applies only for -o'),
        make_option('--scruffy', '', action='store_true', dest='scruffy',
                    help='Make a scuffy diagram')
    )
    args = '[appname appname]'
    help = 'Generating model class diagram for yuml.me'
    label = 'application name'

    YUMLME_URL = "http://yuml.me/diagram/"

    def handle(self, *args, **options):
        if len(args) < 1:
            if options['all_applications']:
                applications = get_apps()
            else:
                raise CommandError("need one or more arguments for appname")
        else:
            try:
                applications = [get_app(label) for label in args]
            except ImproperlyConfigured, e:
                raise CommandError("Specified application not found: %s" % e)
        statments = self.yumlfy(applications)
        if options['outputfile']:
            self.render(statments, **options)
        else:
            print ','.join(statments)

    def yumlfy(self, applications):
        F = YUMLFormatter()
        model_list = []
        arrow_list = []
        external_model = set()
        for app_module in applications:
            models = get_models(app_module)
            if not models:
                continue
            for m in models:
                string = F.label(m) + F.PIPE
                fields = [f for f in m._meta.fields if not f.auto_created]
                for field in fields:
                    string += F.field(field)
                    if field.rel:
                        arrow_list.append(F.relation(m, field.rel))
                        if get_app(field.rel.to._meta.app_label) not in applications:
                            external_model.add(field.rel.to)
                fields = [f for f in m._meta.many_to_many]
                for field in fields:
                    string += F.field(field)
                    if field.rel.through._meta.auto_created:
                        arrow_list.append(F.relation(m, field.rel))
                    else:
                        arrow_list.append(F.through(m, field.rel))
                    if get_app(field.rel.to._meta.app_label) not in applications:
                        external_model.add(field.rel.to)
                model_list.append(F.wrap(string))
                for parent in m._meta.parents:
                    arrow_list.append(F.inherit(m, parent))
                    if get_app(parent._meta.app_label) not in applications:
                        external_model.add(parent)
        for ext in external_model:
            model_list.append(F.external(ext))
        return model_list + arrow_list

    def render(self, statments, **options):
        import urllib2
        import os

        filename     = options['outputfile']
        extension    = os.path.splitext(filename)[1]
        escaped_stat = urllib2.quote(",".join(statments))

        diagram_option = []
        if options['scale']:
            diagram_option.append("scale:%s" % options['scale'])
        if options['scruffy']:
            diagram_option.append("scruffy")
        string_option = ''
        if diagram_option:
            string_option = ';'.join(diagram_option) + '/'
        try:
            yuml_response = urllib2.urlopen("%s%sclass/%s%s" % (self.YUMLME_URL, string_option, escaped_stat, extension))
        except urllib2.HTTPError, e:
            raise CommandError("Error occured while generating %s, %s" % (extension, e))

        resp = yuml_response.read()
        f = open(options['outputfile'], 'w+')
        f.write(resp)
        f.close()
