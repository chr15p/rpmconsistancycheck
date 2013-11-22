#!/usr/bin/python
# Copyright (C) 2013 Chris Procter 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# seth vidal 2005 (c) etc etc



import os
import sys
import yum
from rpmUtils.miscutils import splitFilename
from optparse import OptionParser

rpmlist=[]
filename=""
parser = OptionParser()
parser.add_option("-m", "--master", default=None, action="append", dest="master", help='master channel containing all rpms')
parser.add_option("-e", "--errata", action="append", default=None, dest="errata", help='file containing list of rpms belonging to an errata')
parser.add_option("-d", "--dir", default=None, dest="dir", help='dir containing errata rpms')
parser.add_option("-i", "--install", default=None, action="store_const",const=1, dest="installnew", help='install errata packages not already installed')
parser.add_option("-r", "--repo", action="append", default=None, dest="repolist", help='list of channels to check')

(opt,args) = parser.parse_args()

erratapkgs=[]
if type(opt.errata) == None:
	for e in opt.errata:
		for line in open(e):
			erratapkgs.append(yum.packages.YumLocalPackage(filename=opt.dir+"/"+line.rstrip('\n')))

yb = yum.YumBase()
yb.setCacheDir()
yb.repos.disableRepo('*')
if type(opt.repolist) == None:
	for repo in opt.repolist:
		repedetails=repo.split(",")
		newrepo = yum.yumRepo.YumRepository(repodetails[0])
		newrepo.baseurl = repodetails[1]

yb.pkgSack = yb.repos.populateSack(mdtype='metadata',cacheonly=1) #which='enabled',
repopkgobjs = dict()
for i in yb.pkgSack.returnPackages():
	repopkgobjs[i.name]=i
	

yb.repos.disableRepo('*')

#repolist=[ "fedora-clone","updates-clone" ]
for repo in opt.master:
	repodetails=repo.split(",")
	newrepo = yum.yumRepo.YumRepository(repodetails[0])
	newrepo.baseurl =repodetails[1] #"file:///home/chrisp/projects/prospero/19/fedora-clone/"
	newrepo.metadata_expire = 0
	newrepo.timestamp_check = False
	yb.repos.add(newrepo)
	yb.repos.enableRepo(repodetails[0])

yb.pkgSack = yb.repos.populateSack(mdtype='metadata',cacheonly=1) #which='enabled',
#print yb.pkgSack.returnPackages()
#sys.exit(0)


### replace any from the errata list that are newer then the installed package that matches 
for e in erratapkgs:
	if repopkgobjs.get(e.name) and e.verGT(repopkgobjs[e.name]):
		repopkgobjs[e.name]=e
	elif repopkgobjs.get(e.name) and e.verLT(repopkgobjs[e.name]):
		print "%s-%s-%s.%s older then installed"%(e.name, e.version, e.release,e.arch)
	elif repopkgobjs.get(e.name) and e.verEQ(repopkgobjs[e.name]):
		print "%s-%s-%s.%s already installed"%(e.name, e.version, e.release,e.arch)
	elif repopkgobjs.get(e.name,"") == "" and opt.installnew:
		repopkgobjs[e.name]=e
	else:
		yb.pkgSack.add(e)
	
try:
	deps = yb.findDeps(repopkgobjs.values())
except Exception as e:
	for i in repopkgobjs.values():
		print "%s=%s"%(i,type(i))
	print e
	sys.exit(0)

pkgs=dict()
for i in deps.keys():				### packages
	for j in deps[i].keys():		### requirements for package
		if deps[i][j] == []:
			continue
		
		for k in deps[i][j]:		### potential resolutions for requirements
			name="%s-%s-%s.%s"%(k.name, k.version, k.release,k.arch)
			if name in rpmlist:		### there is something installed that satisfies the dep
				break
			#elif pkgobjlist.get(name,"") != "":	### there is something in the repo that satisfies the dep
			#	break
		else:						### there is nothing available anywhere that satisfies the dep
			print "%s-%s-%s.%s requires %s"%(i.name, i.version, i.release,i.arch," ".join([m.name for m in deps[i][j]]))
			pkgs[name]=1

print "================"
for i in pkgs.keys():
	print i


sys.exit(0)
