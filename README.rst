====================
Django Yuml
====================

Generates YUML class diagram for you django project or specified apps in project

http://yuml.me

Installation
================
#. Add the `django_yuml` directory to your Python path.

#. Add `django_yuml` to your `INSTALLED_APPS` setting so Django can find it.


Examples
================

#. python manage.py yourapp yoursecondapp --scruffy -s 75 -o test.png

#. python manage.py justoneapp --scruffy -o test.pdf

#. generate whole project yuml
   
   python manage.py -a -o test.jpg

#. python manage.py yuml auth contenttypes sessions admin -o test.pdf

This is how looks generated diagram for command: 

- python manage.py yuml auth contenttypes sessions sites messages admin --scruffy --scale 100 -o example.jpg

  http://www.gang.lt/example.jpg