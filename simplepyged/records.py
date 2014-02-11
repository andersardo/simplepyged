#-*- coding: utf-8 -*-
#
# Gedcom 5.5 Parser
#
# Copyright (C) 2010 Nikola Škorić (nskoric [ at ] gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# Please see the GPL license at http://www.gnu.org/licenses/gpl.txt
#
# To contact the author, see http://github.com/dijxtra/simplepyged

# Global imports
import string
from itertools import groupby
from events import Event

class MultipleReturnValues(Exception):
    pass

class Line:
    """ Line of a GEDCOM file

    Each line in a Gedcom file has following format:

    level [xref] tag [value]

    where level and tag are required, and xref and value are optional.
    Lines are arranged hierarchically according to their level, and
    lines with a level of zero (called 'records') are at the top
    level.  Lines with a level greater than zero are children of their
    parent.

    A xref has the format @pname@, where pname is any sequence of
    characters and numbers.  The xref identifies the record being
    referenced to, so that any xref included as the value of any line
    points back to the original record.  For example, an line may have
    a FAMS tag whose value is @F1@, meaning that this line points to
    the family record in which the associated individual is a spouse.
    Likewise, an line with a tag of FAMC has a value that points to a
    family record in which the associated individual is a child.
    
    See a Gedcom file for examples of tags and their values.

    """

    def __init__(self,level,xref,tag,value,dict):
        """ Initialize a line.  You must include a level, xref,
        tag, value, and global line dictionary.  Normally initialized
        by the Gedcom parser, not by a user.
        """
        # basic line info
        self._level = level
        self._xref = xref
        self._tag = tag
        self._value = value
        self._dict = dict
        # structuring
        self._children_lines = []
        self._parent_line = None

    def _init(self):
        """ A method which GEDCOM parser runs after all lines are available. Subclasses should implement this method if they want to work with other Lines at parse time, but after all Lines are parsed. """
        pass

    def type(self):
        """ Return class name of this instance

        Useful for determining if this line is Individual, Family, Note or some other record.
        """
        return self.__class__.__name__

    def level(self):
        """ Return the level of this line """
        return self._level

    def xref(self):
        """ Return the xref of this line """
        return self._xref
    
    def tag(self):
        """ Return the tag of this line """
        return self._tag

    def value(self):
        """ Return the value of this line """
        return self._value

    def children_lines(self):
        """ Return the child lines of this line """
        return self._children_lines

    def parent_line(self):
        """ Return the parent line of this line """
        return self._parent_line

    def add_child(self,line):
        """ Add a child line to this line """
        self.children_lines().append(line)
        
    def add_parent_line(self,line):
        """ Add a parent line to this line """
        self._parent_line = line

    def children_tags(self, tag):
        """ Returns list of child lines whos tag matches the argument. """
        lines = []
        for c in self.children_lines():
            if c.tag() == tag:
                lines.append(c)

        return lines

    def children_tag_records(self, tag):
        """ Returns list of records which are pointed by child lines with given tag. """
        lines = []
        for e in self.children_tags(tag):
            try:
                lines.append(self._dict[e.value()])
            except KeyError:
                pass

        return lines

    def gedcom(self):
        """ Return GEDCOM code for this line and all of its sub-lines """
        result = unicode(self)
        for e in self.children_lines():
            result += '\n' + e.gedcom()
        return result

    def __str__(self):
        """ Format this line as its original string """
        result = unicode(self.level())
        if self.xref() != "":
            result += ' ' + self.xref()
        result += ' ' + self.tag()
        if self.value() != "":
            result += ' ' + self.value()
        return result


class Record(Line):
    """ Gedcom line with level 0 represents a record

    Child class of Line

    """
    
    def _parse_generic_event_list(self, tag):
        """ Creates new event for each line with given tag"""
        retval = []
        for event_line in self.children_tags(tag):
            retval.append(Event(event_line))

        return retval


class Multimedia(Record):
    pass


class Note(Record):
    pass


class Repository(Record):
    pass


class Source(Record):
    pass


class Submission(Record):
    pass


class Submitter(Record):
    pass


class Individual(Record):
    """ Gedcom record representing an individual

    Child class of Record

    """

    def __init__(self,level,xref,tag,value,dict):
        Record.__init__(self,level,xref,tag,value,dict)

    def _init(self):
        """ Implementing Line._init() """
        self._parent_families = self.get_parent_families()
        self._families = self.get_families()

        self.birth_events = self._parse_generic_event_list("BIRT")
        self.death_events = self._parse_generic_event_list("DEAT")
        self.other_events = []
        for event_type in ["ADOP", "BAPM", "BARM", "BASM", "BLES", "BURI",
                           "CENS", "CHR", "CHRA", "CONF", "CREM", "EMIG",
                           "FCOM", "GRAD", "IMMI", "NATU", "ORDN", "RETI",
                           "PROB", "WILL", "EVEN"]:
            self.other_events.extend(self._parse_generic_event_list(event_type))

    def sex(self):
        """ Returns 'M' for males, 'F' for females, or None if not specified """
        try:
            return self.children_tags("SEX")[0].value()
        except IndexError:
            return None

    def parent_families(self):
        return self._parent_families

    def parent_family(self):
        if len(self.parent_families()) == 0:
            return None

        if len(self.parent_families()) == 1:
            return self.parent_families()[0]

        if len(self.parent_families()) > 1:
            raise MultipleReturnValues("Individual has multiple parent families.")

    def families(self):
        return self._families

    def family(self):
        if len(self.families()) == 0:
            return None

        if len(self.families()) == 1:
            return self.families()[0]

        if len(self.families()) > 1:
            raise MultipleReturnValues("Individual has multiple families.")

    def father(self):
        """Returns a father as an Individual object. If person has multiple fathers, returns a list of Individual objects. """
        fathers = []

        for family in self.parent_families():
            if family.husband() != None:
                fathers.append(family.husband())

        if len(fathers) == 1:
            return fathers[0]

        return fathers

    def mother(self):
        """Returns a mother as an Individual object. If person has multiple mothers, returns a list of Individual objects. """
        mothers = []

        for family in self.parent_families():
            if family.wife() != None:
                mothers.append(family.wife())

        if len(mothers) == 1:
            return mothers[0]

        return mothers

    def children(self):
        retval = []

        for f in self.families():
            for c in f.children():
                retval.append(c)

        return retval

    def siblings(self):
        siblings = []

        for family in self.parent_families():
            for child in family.children():
                if child != self:
                    siblings.append(child)

        return siblings

    def get_families(self):
        """ Return a list of all of the family records of a person. """
        return self.children_tag_records("FAMS")

    def get_parent_families(self):
        """ Return a list of all of the family records in which this individual is a child. (adopted children can have multiple parent families)"""
        return self.children_tag_records("FAMC")
    
    def name(self):
        """ Return a person's names as a tuple: (first,last) """
        first = ""
        last = ""
        for e in self.children_lines():
            if e.tag() == "NAME":
                # some older Gedcom files don't use child tags but instead
                # place the name in the value of the NAME tag
                if e.value() != "":
                    name = string.split(e.value(),'/')
                    first = string.strip(name[0])
                    last = string.strip(name[1]) if len(name) > 1 else None
                else:
                    for c in e.children_lines():
                        if c.tag() == "GIVN":
                            first = c.value()
                        if c.tag() == "SURN":
                            last = c.value()
        return (first,last)

    def given_name(self):
        """ Return person's given name """
        try:
            return self.name()[0]
        except IndexError:
            return None

    def surname(self):
        """ Return person's surname """
        try:
            return self.name()[1]
        except IndexError:
            return None

    def fathers_name(self):
        """ Return father's name (patronymic) """
        return self.father().given_name()
        
    def birth(self):
        """ Return one randomly chosen birth event

        If a person has only one birth event (which is most common
        case), return that one birth event. For list of all birth
        events see self.birth_events.
        """

        if len(self.birth_events) == 0:
            return None

        return self.birth_events[0]

    def birth_year(self):
        """ Return the birth year of a person in integer format """

        if self.birth() == None:
            return -1

        if self.birth().date == None:
            return -1

        try:
            date = int(string.split(self.birth().date)[-1])
            return date
        except ValueError:
            return -1

    def alive(self):
        """ Return True if individual lacks death entry """
        return self.death() is None

    def death(self):
        """ Return one randomly chosen death event

        If a person has only one death event (which is most common
        case), return that one death event. For list of all death
        events see self.death_events.
        """

        if len(self.death_events) == 0:
            return None

        return self.death_events[0]

    def death_year(self):
        """ Return the death year of a person in integer format """

        if self.death() == None:
            return -1

        if self.death().date == None:
            return -1

        try:
            date = int(string.split(self.death().date)[-1])
            return date
        except ValueError:
            return -1

    def deceased(self):
        """ Check if a person is deceased """
        return not self.alive()

    def marriages(self):
        """ Return a list of marriage events for a person.
        """
        retval = []

        for f in self.families():
            for marr in f.marriage_events:
                retval.append(marr)

        return retval

    def marriage_years(self):
        """ Return a list of marriage years for a person, each in integer
        format.
        """
        def ret_year(marr):
            if marr.date is None:
                return ''
            return int(marr.date.split(" ")[-1])

        return map(ret_year, self.marriages())

    def parents(self):
        """ Return list of parents of this Individual """

        parent_pairs = map(lambda x: x.parents(), self.parent_families())

        return [parent for parent_pair in parent_pairs for parent in parent_pair]   

    def common_ancestor(self, relative):
        """ Find a common ancestor with a relative. """
        common_ancestors = self.common_ancestors(relative)

        if relative is None:
            return None

        if len(common_ancestors) == 0:
            return None

        if len(common_ancestors) == 1:
            return common_ancestors[0]

        if len(common_ancestors) > 1:
            raise MultipleReturnValues("Individual has multiple common ancestors with that relative.")

        

    def common_ancestors(self, relative):
        """ Find all common ancestors with a relative. """

        if relative is None:
            return []

        common_ancestors = []

        for family in self.common_ancestor_families(relative):
            for ancestor in family.parents():
                if not (ancestor in common_ancestors):
                    common_ancestors.append(ancestor)

        return common_ancestors
        

    def common_ancestor_families(self, relative):
        """ Find a common ancestor family with a relative. """

        if relative is None:
            return []

        mutual = self.mutual_parent_families(relative)
        if mutual:
            return mutual

        my_ancestors = self.ancestor_families_with_distance()
        if not my_ancestors:
            return []

        his_ancestors = relative.ancestor_families_with_distance()
        if not his_ancestors:
            return []

        my_anc_without_dist = map(lambda (fam, dist): fam, my_ancestors)
        his_anc_without_dist = map(lambda (fam, dist): fam, his_ancestors)

        common_without_dist = list(set(my_anc_without_dist) & set(his_anc_without_dist))
        if not common_without_dist:
            return []

        common_with_my_dist = filter(lambda (fam, dist): fam in common_without_dist, my_ancestors)

        (fam, min_dist) = min(common_with_my_dist, key = lambda (fam, dist): dist)

        common_min_with_dist = filter(lambda (fam, dist): dist == min_dist, common_with_my_dist)

        return map(lambda (fam, dist): fam, common_min_with_dist)
            
    def mutual_parent_families(self, candidate):
        """Return mutual parent families of self and candidate. If self na candidate are not siblings, it will return empty list."""

        return list(set(self.parent_families()) & set(candidate.parent_families()))
                

    def is_parent(self, candidate):
        """ Determine if candidate is parent of self """
        if candidate in self.parents():
            return True

        return False
        
    def is_sibling(self, candidate):
        """ Determine if candidate is sibling of self """
        if self.mutual_parent_families(candidate):
            return True

        return False
        
    def is_relative(self, candidate):
        """ Determine if candidate is relative of self """

        if self.is_ancestor(candidate):
            return True
            
        if candidate.is_ancestor(self):
            return True
            
        if self.common_ancestor_families(candidate):
            return True

        return False

    def is_ancestor(self, candidate):
        """ Determine if candidate is ancestor of self """

        if self.is_parent(candidate):
            return True

        for parent in self.parents():
            if parent.is_ancestor(candidate):
                return True

        return False

        
    def distance_to_ancestor(self, ancestor):
        """Distance to an ancestor given in number of generations

        Examples of return value:
        * from self to self: 0
        * from self to father: 1
        * from self to mother: 1
        * from self to grandfather: 2 """

        distance = 0
        ancestor_list = [self]

        while ancestor_list != []:
            if ancestor in ancestor_list:
                return distance

            new_list = []
            for a in ancestor_list:
                new_list.extend(a.parents())

            ancestor_list = new_list

            distance += 1

        return None

    @staticmethod
    def down_path(ancestor, descendant, distance = None):
        """ Return path between ancestor and descendant (do not go deeper than distance depth) """

        if distance is not None:
            if distance <= 0:
                return None

        if ancestor == descendant:
            return [ancestor]
            
        if ancestor.children() == []:
            return None
        
        if descendant in ancestor.children():
            return [ancestor, descendant]

        for c in ancestor.children():
            if distance is None:
                path = ancestor.down_path(c, descendant)
            else:
                path = ancestor.down_path(c, descendant, distance - 1)
            if path is not None:
                path.insert(0, ancestor)
                return path
    
        return None

    def path_to_relative(self, relative, compact = False):
        """ Find path to a relative

        Returns a list of tuples (ancestor, direction) where:
        * ancestor is a person in the path between self and relative
        * direction is 'up' if this step in the path is parent of previous step
        * direction is 'down' if this step in the path is child of previous step
        """

        if relative == self:
            return [(self, 'start')]

        if relative in self.parents():
            return [(self, 'start'), (relative, 'parent')]
        
        if relative in self.children():
            return [(self, 'start'), (relative, 'child')]
        
        common_ancestors = self.common_ancestors(relative)

        if not common_ancestors: # is not relative
            return None

        common_ancestor = common_ancestors[0]

        if self in common_ancestors:
            my_path = []
        else:
            my_path = self.down_path(common_ancestor, self, self.distance_to_ancestor(common_ancestor))

        if relative in common_ancestors:
            his_path = []
        else:
            his_path = self.down_path(common_ancestor, relative, relative.distance_to_ancestor(common_ancestor))

        my_path.reverse()
        his_path.reverse()

        if relative in my_path:
            old_path = my_path
            my_path = []
            for step in old_path:
                my_path.append(step)
                if step == relative:
                    break
            his_path = [relative]

        if self in his_path:
            old_path = his_path
            his_path = []
            for step in old_path:
                his_path.append(step)
                if step == self:
                    break
            my_path = [self]

        his_path.reverse()

        full_path = [(self, 'start')]
        for step in my_path[1:]: #my path with common ancestor
            full_path.append((step, 'parent'))

        print map(lambda x: x.xref(), my_path)
        print map(lambda x: x.xref(), his_path)
        print map(lambda (x, y): (x.xref(), y), full_path)

        if compact:
            # if two children of common ancestor are siblings, then leave
            # out common ancestor
            try:
                if full_path[-1][0].is_sibling(his_path[1]):
                    full_path[-1][1] = 'sibling'
                else: # children of common ancestor are half-siblings, so
                      # we won't leave common ancestor out
                    full_path.append([common_ancestor, 'child'])
            except IndexError: # sibling check didn't work out, we'll just
                               # put common ancestor in there
                full_path.append([common_ancestor, 'child'])
        
        for step in his_path[1:]: #his path without common ancestor
            full_path.append((step, 'child'))

        print map(lambda (x, y): (x.xref(), y), full_path)

        return full_path
        
    def ancestor_families_with_distance(self):
        """For each family ancestor to this one return list of tuples (family, distance)."""

        ancestor_families = []

        for fam in self.parent_families():
            ancestor_families.append((fam, 0))
            ancestor_families.extend(fam._ancestor_families_with_distance(1))

        return sorted(ancestor_families, key=lambda (fam, dist): dist)

        
class Family(Record):
    """ Gedcom record representing a family

    Child class of Record

    """

    def __init__(self,level,xref,tag,value,dict):
        Record.__init__(self,level,xref,tag,value,dict)

    def _init(self):
        """ Implementing Line._init()

        Initialise husband, wife and children attributes. """
        
        try:
            self._husband = self.children_tag_records("HUSB")[0]
        except IndexError:
            self._husband = None

        try:
            self._wife = self.children_tag_records("WIFE")[0]
        except IndexError:
            self._wife = None

        try:
            self._children = self.children_tag_records("CHIL")
        except IndexError:
            self._children = []

        self.marriage_events = self._parse_generic_event_list("MARR")
        self.other_events = []
        for event_type in ["ANUL", "CENS", "DIV", "DIVF", "ENGA", "MARB",
                           "MARC", "MARL", "MARS", "EVEN"]:
            self.other_events.extend(self._parse_generic_event_list(event_type))

    def husband(self):
        """ Return husband this family """
        return self._husband

    def wife(self):
        """ Return wife this family """
        return self._wife

    def parents(self):
        """ Return list of parents in this family """
        parents = []

        if self._husband:
            parents.append(self._husband)
        if self._wife:
            parents.append(self._wife)
        
        return parents

    def children(self):
        """ Return list of children in this family """
        return self._children

    def married(self):
        """ Return True if parents were married """
        return len(self.children_tags("MARR")) > 0

    def marriage(self):
        """ Return one randomly chosen marriage event

        If a family has only one marriage event (which is most common
        case), return that one marriage event. For list of all marriage
        events see self.marriage_events.
        """

        return self.marriage_events[0]

    def is_relative(self, candidate):
        """ Determine if candidate is relative of a member of family """
        if self.husband() is not None and self.husband().is_relative(candidate):
            return True

        if self.wife() is not None and self.wife().is_relative(candidate):
            return True

        return False

    def parent_families(self):
        """Return list of families which are parent to this one."""

        parent_families = []
        
        if self.husband():
            husband_families = self.husband().parent_families()
            if husband_families:
                parent_families.extend(husband_families)

        if self.wife():
            wife_families = self.wife().parent_families()
            if wife_families:
                parent_families.extend(wife_families)

        return parent_families

    def ancestor_families_with_distance(self):
        """For each family ancestor to this one return list of tuples (family, distance)."""
        return sorted(self._ancestor_families_with_distance(0), key=lambda (fam, dist): dist)
        
    def _ancestor_families_with_distance(self, distance):
        parent_families = self.parent_families()

        anc_fam = []

        for fam in parent_families:
            anc_fam.append((fam, distance))

        for fam in parent_families:
            anc_fam.extend(fam._ancestor_families_with_distance(distance + 1))

        return anc_fam
