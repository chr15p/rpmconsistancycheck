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

repolist=opt.repolist or []
for repo in repolist:
	repodetails=repo.split(",")
	newrepo = yum.yumRepo.YumRepository(repodetails[0])
	newrepo.baseurl = repodetails[1]
	yb.repos.add(newrepo)
	yb.repos.enableRepo(repodetails[0])

yb.pkgSack = yb.repos.populateSack(mdtype='metadata',cacheonly=1) #which='enabled',

repopkgobjs=dict()
for i in yb.pkgSack.returnPackages():
	repopkgobjs[i]=1

#print repopkgobjs
yb.repos.disableRepo('*')

#repolist=[ "fedora-clone","updates-clone" ]
master = opt.master  or [] 
for repo in master:
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
for e in erratapkgs:
	if repopkgobjs.get(e):
		print "%s-%s-%s.%s already in repos"%(e.name, e.version, e.release,e.arch)
	else:
		repopkgobjs[e]=1

#print "a"

try:
	deps = yb.findDeps(repopkgobjs.keys())
except Exception as e:
	#for i in repopkgobjs.values():
	#	print "%s=%s"%(i,type(i))
	print e
	sys.exit(0)

#print "b"
#print deps
#sys.exit(0)

pkgs=dict()
for i in deps.keys():				### packages
	#print i.name
	#print deps[i]
	#sys.exit(0)
	for j in deps[i].keys():		### requirements for package
		if deps[i][j] == []:		### no dependancies required
			continue
	
		#print "======" + i.name 
		#print deps[i][j]	
		for k in deps[i][j]:		### potential resolutions for requirements
			if repopkgobjs.get(k):
				#print k
				break
		else:
			print "%s-%s-%s.%s requires one of:"%(i.name, i.version, i.release,i.arch)
			for m in deps[i][j]:
				print "\t%s-%s-%s.%s"%(m.name, m.version, m.release,m.arch)
				


sys.exit(0)
