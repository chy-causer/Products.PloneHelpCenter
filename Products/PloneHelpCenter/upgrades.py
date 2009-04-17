#!/usr/bin/env python
# encoding: utf-8
"""
upgrades.py

Created by Steve McMahon on 2009-04-17.
"""

from config import PROJECTNAME

from zope.component import getUtility
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName

# getPortal and IfInstalled stolen from Collage.
# Thanks, Giles!

def getPortal():
    return getUtility(ISiteRoot)

class NotInstalledComponent(LookupError):
    def __init__(self, cpt_name):
        self.cpt_name = cpt_name
        return

    def __str__(self):
        msg = ("Component '%s' is not installed in this site."
               " You can't run its upgrade steps."
               % self.cpt_name)
        return msg

class IfInstalled(object):
    def __init__(self, prod_name=PROJECTNAME):
        """@param prod_name: as shown in quick installer"""
        self.prod_name = prod_name

    def __call__(self, func):
        """@param func: the decorated function"""
        def wrapper(setuptool):
            qi = getPortal().portal_quickinstaller
            installed_ids = [p['id'] for p in qi.listInstalledProducts()]
            if self.prod_name not in installed_ids:
                raise NotInstalledComponent(self.prod_name)
            return func(setuptool)
        wrapper.__name__ = func.__name__
        wrapper.__dict__.update(func.__dict__)
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        return wrapper
        
def migrateBodyTexts(self):

    catalog = getToolByName(self, 'portal_catalog')
    brains = catalog(
        portal_type=['HelpCenterReferenceManualPage',
                     'HelpCenterTutorialPage',
                     'HelpCenterHowTo',
                     'HelpCenterErrorReference',
                     ],
        path='/'.join(self.getPhysicalPath())        
    )

    res = ['Migrate Page Texts ...']
    for obj in [brain.getObject() for brain in brains]:
        body = getattr(obj, 'body', None)
        if body:
            obj.setText(body)
            delattr(obj, 'body')
            res.append(obj.id)

    return "\n".join(res)


def migrateFAQs(self):

    catalog = getToolByName(self, 'portal_catalog')
    brains = catalog(
        portal_type=['HelpCenterFAQ',],
        path='/'.join(self.getPhysicalPath())        
    )

    res = ['Migrate FAQ Answers ...']
    for obj in [brain.getObject() for brain in brains]:
        body = getattr(obj, 'answer', None)
        if body:
            obj.setText(body)
            delattr(obj, 'answer')
            res.append(obj.id)

    return "\n".join(res)


def migrateNextPrev(self):

    catalog = getToolByName(self, 'portal_catalog')
    brains = catalog(
        portal_type=[
            'HelpCenterReferenceManual',
            'HelpCenterReferenceManualSection',
            'HelpCenterTutorial',
            ],
        path='/'.join(self.getPhysicalPath())        
    )

    res = ['Turn on next/prev navigation ...']
    for obj in [brain.getObject() for brain in brains]:
        if not obj.getNextPreviousEnabled():
            obj.setNextPreviousEnabled(True)
            res.append(obj.id)

    return "\n".join(res)

@IfInstalled()        
def runTypesMigration(setuptool):
    """
        Migrate to 3+ types
    """
    
    portal = getPortal()
    print migrateNextPrev(portal)
    print migrateBodyTexts(portal)
    print migrateFAQs(portal)

    return