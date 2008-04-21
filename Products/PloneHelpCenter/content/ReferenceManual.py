try:
    from Products.LinguaPlone.public import *
except ImportError:
    # No multilingual support
    from Products.Archetypes.public import *
from Products.PloneHelpCenter.config import *
try:
    import Products.CMFCore.permissions as CMFCorePermissions
except ImportError:
    from Products.CMFCore import CMFCorePermissions
from schemata import HelpCenterBaseSchema, HelpCenterItemSchema
from PHCContent import PHCContent
from Products.CMFCore.utils import getToolByName
from AccessControl import ClassSecurityInfo, ModuleSecurityInfo
from Products.CMFPlone.browser.navtree import NavtreeStrategyBase, buildFolderTree

import re
IMG_PATTERN = re.compile(r"""(\<img .*?)src="([^/]+?)"(.*?\>)""", re.IGNORECASE | re.DOTALL)


ReferenceManualSchema = HelpCenterBaseSchema + Schema((
    TextField(
        'description',
        default='',
        searchable=1,
        required=1,
        primary=1,
        accessor="Description",
        default_content_type = 'text/plain',
        allowable_content_types = ('text/plain',),
        storage=MetadataStorage(),
        widget=TextAreaWidget(
                description='A summary of the reference manual -- subject and scope. Will be displayed on every page of the manual.',
                description_msgid="phc_help_referencemanual_summary",
                label="Reference Manual Description",
                label_msgid="phc_label_referencemanual_description",
                rows=5,
                i18n_domain="plonehelpcenter",
                ),
        ),
    ),)  + HelpCenterItemSchema

# For some reason, we need to jump through these hoops to get the fields in the
# the right order
ReferenceManualSchema.moveField('subject', pos='bottom')
ReferenceManualSchema.moveField('relatedItems', pos='bottom')


class HelpCenterReferenceManual(PHCContent,OrderedBaseFolder):
    """A reference manual containing ReferenceManualPages,
    ReferenceManualSections, Files and Images.
    """

    __implements__ =(PHCContent.__implements__,
                      OrderedBaseFolder.__implements__,)

    schema = ReferenceManualSchema
    archetype_name = 'Reference Manual'
    meta_type='HelpCenterReferenceManual'
    content_icon = 'referencemanual_icon.gif'

    global_allow = 0
    filter_content_types = 1
    allowed_content_types =('HelpCenterReferenceManualPage', 
                             'HelpCenterReferenceManualSection', 
                             'Image', 'File')
    # allow_discussion = IS_DISCUSSABLE

    security = ClassSecurityInfo()

    typeDescription= 'A Reference Manual can contain Reference Manual Pages and Sections, Images and Files. Index order is decided by the folder order, use the normal up/down arrow in the folder content view to rearrange content.'
    typeDescMsgId  = 'description_edit_referencemanual'

    security.declareProtected(CMFCorePermissions.View,
                                'getReferenceManualDescription')
    def getReferenceManualDescription(self):
        """ Returns the description of the ReferenceManual -- 
        convenience method for ReferenceManualPage
        """
        return self.Description()

    security.declareProtected(CMFCorePermissions.View, 'getTOC')
    def getTOC(self, current=None, root=None):
        """Get the table-of-contents of this manual. 
        
        The parameter 'current' gives the object that is the current page or
        section being viewed. 
        
        The parameter 'root' gives the root of the manual - if not given, this
        ReferenceManual object is used, but you can pass in a 
        ReferenceManualSection instead to root the TOC at this element. The 
        root element itself is not included in the table-of-contents.
        
        The return value is a list of dicts, recursively representing the 
        table-of-contents of this manual. Each element dict contains:
        
            item        -- a catalog brain for the item (a section or page)
            numbering   -- The dotted numbering of this item, e.g. 1.3.2
            depth       -- The depth of the item (0 == top-level item)
            currentItem -- True if this item corresponds to the object 'current'
            children    -- A list of dicts
            
        The list 'children' recursively contains the equivalent dicts for
        children of each section. If the parameter 'current' is not given, no
        element will have current == True.
        """

        if not root:
            root = self

        class Strategy(NavtreeStrategyBase):
            
            rootPath = '/'.join(root.getPhysicalPath())
            showAllParents = False
                
        strategy = Strategy()
        query=  {'path'        : '/'.join(root.getPhysicalPath()),
                 'portal_type' : ('HelpCenterReferenceManualSection',
                                   'HelpCenterReferenceManualPage',),
                 'sort_on'     : 'getObjPositionInParent'}
                
        toc = buildFolderTree(self, current, query, strategy)['children']
        
        def buildNumbering(nodes, base=""):
            idx = 1
            for n in nodes:
                numbering = "%s%d." % (base, idx,)
                n['numbering'] = numbering
                buildNumbering(n['children'], numbering)
                idx += 1
                
        buildNumbering(toc)
        return toc

    security.declareProtected(CMFCorePermissions.View, 'getTOCInfo')
    def getTOCInfo(self, toc):
        """Get information about a table-of-contents, as returned by getTOC.
        
        The return value is a dict, containing:

            tocList    -- A flat list representing the table-of-contents
            localTOC   -- A toc structure for the contents under the current
                            item (passed in as 'current' to getTOC())
            currentIdx -- The index in tocList of 'current'
            nextIdx    -- The index in tocList of the next item after 'current'
            prevIdx    -- The index in tocList of the next item before 'current'
            parentIdx  -- The index in tocList of the parent of 'current'
            
        The elements 'currentIdx', 'nextIdx', 'prevIdx' and 'parentIdx' may be
        None if either the table-of-contents was not constructed with a current
        item, or if there is no previous/next/parent item. Similarly, 'localTOC' 
        will be None if the table-of-contents was not constructed with a current 
        item.
        
        Each item in the list 'tocList' in the returned dict contains a dict 
        with keys:
        
            item       -- A catalog brain repsenting the item
            numbering  -- The dotted numbering of the item, e.g. 1.3.2.
            depth      -- The depth of the item (0 = top-level item)
            current    -- True if this item represents the current page/section
         
        The parameter 'toc' gives the table of contents, as returned by
        getTOC() above.
        """

        # Let's fake static variables - keep track of what may be our parent
        global parentIdx, prevIdx, prevDepth, prevWasCurrent

        parentIdx = None
        prevIdx = None
        prevDepth = -1
        prevWasCurrent = False

        def addToList(tocInfo, tocItem):
            item      = tocItem['item']
            numbering = tocItem['numbering']
            depth     = tocItem['depth']
            children  = tocItem['children']
            isCurrent = tocItem['currentItem']

            global parentIdx, prevIdx, prevDepth, prevWasCurrent

            numberingList = numbering.split('.')[:-1]
            idxList = [int(number) - 1 for number in numberingList]

            tocInfo['tocList'].append({'item'        : item,
                                       'numbering'   : numbering,
                                       'depth'       : depth,
                                       'currentItem' : isCurrent,
                                       })

            currentIdx = len(tocInfo['tocList']) - 1

            if isCurrent:
                prevWasCurrent = True
                tocInfo['currentIdx'] = currentIdx
                if currentIdx > 0:
                    tocInfo['prevIdx'] = currentIdx - 1
                tocInfo['parentIdx'] = parentIdx
                tocInfo['localTOC'] = tocItem['children']
            elif prevWasCurrent:
                prevWasCurrent = False
                tocInfo['nextIdx'] = currentIdx

            for child in children:
                addToList(tocInfo, child)

            # parent index will be item with depth = depth - 1
            # keep track of potential parents by noting when we move down
            # one step

            if depth > prevDepth:
                parentIdx = prevIdx
                prevDepth = depth

            prevIdx = currentIdx

        tocInfo = {'currentIdx' : None,
                   'nextIdx'    : None,
                   'prevIdx'    : None,
                   'parentIdx'  : None,
                   'tocList'    : [],
                   'localTOC'   : None}

        for topLevel in toc:
            addToList(tocInfo, topLevel)

        return tocInfo

    security.declareProtected(CMFCorePermissions.View, 'addImagePaths')
    def addImagePaths(self, body, baseurl):
        """Fixup image paths in section body"""
        
        # This is a convenience method for use in referencemanual_macros
        # section_collation macro. It looks in body for img tags
        # with relative URLs in the src attribute and prepends the baseurl.
        # TODO: when we not longer need 2.1 compatibility, this belongs in 
        # a view.
                
        return IMG_PATTERN.sub(r"""\1src="%s/\2"\3""" % baseurl, body)


registerType(HelpCenterReferenceManual, PROJECTNAME)
