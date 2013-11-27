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

import os
import sys
import yum
from rpmUtils.miscutils import splitFilename
from optparse import OptionParser

rpmlist=[]
filename=""
parser = OptionParser()
parser.add_option("-f", "--file", default=None, dest="filename", help='file containing list of rpms to check')
parser.add_option("-e", "--errata", action="append", default=None, dest="errata", help='file containing list of rpms belonging to an errata')
parser.add_option("-d", "--dir", default=None, dest="dir", help='dir containing errata rpms')
parser.add_option("-r", "--repo", action="append", default=None, dest="repolist", help='id of a repo to check against')

(opt,args) = parser.parse_args()
filename = opt.filename or sys.exit(1)
repolist = opt.repolist or sys.exit(1)
errata = opt.errata or ""
rpmdir = opt.dir or "."

## read the rpms from a file
#rpmlist = [line.rstrip('\n') for line in open(opt.filename)]
for line in open(filename):
	rpmlist.append(line.rstrip('\n'))

erratapkgs=[]
for e in errata:
	for line in open(e):
		erratapkgs.append(yum.packages.YumLocalPackage(filename=rpmdir+"/"+line.rstrip('\n')))

yb = yum.YumBase()
yb.setCacheDir("/var/cache/yum/")

conrepos=[]
for i in yb.repos.findRepos("*"):
	conrepos.append(i.getAttribute("id"))


yb.repos.disableRepo('*')

#repolist=[ "fedora-clone","updates-clone" ]
for repo in repolist:
	if repo not in conrepos:
		newrepo = yum.yumRepo.YumRepository(repo)
		newrepo.metadata_expire = 0
		newrepo.timestamp_check = False
		yb.repos.add(newrepo)
	
	yb.repos.enableRepo(repo)

yb.pkgSack = yb.repos.populateSack(mdtype='metadata',cacheonly=1) #which='enabled',

pkgobjlist=dict()
for i in yb.pkgSack:
	#print "%s-%s-%s.%s"%(i.name, i.version, i.release,i.arch)
	pkgobjlist["%s-%s-%s.%s"%(i.name, i.version, i.release,i.arch)]=i

instpkgobjs = dict()
for rpmname in rpmlist:
	#print rpm
	rpm = pkgobjlist.get(rpm,"")
	if rpm =="":
		try:
			rpm = yum.packages.YumLocalPackage(filename= rpmdir + "/" + rpmname + ".rpm")
		except:
			print "NOT FOUND IN REPOs: " +rpmname
			continue
	#instpkgobjs.append(rpmname)
	instpkgobjs[rpm]=1



### replace any from the errata list that are newer then the installed package that matches e
for e in erratapkgs:
	if instpkgobjs.get(e) and e.verGT(instpkgobjs[e]):
		instpkgobjs[e]=1
	elif instpkgobjs.get(e) and e.verLT(instpkgobjs[e]):
		print "%s-%s-%s.%s older then installed"%(e.name, e.version, e.release,e.arch)
	elif instpkgobjs.get(e) and e.verEQ(instpkgobjs[e]):
		print "%s-%s-%s.%s already installed"%(e.name, e.version, e.release,e.arch)
	elif instpkgobjs.get(e,"") == "" and opt.installnew:
		instpkgobjs[e]=1
	else:
		yb.pkgSack.addPackage(e)

try:
	deps = yb.findDeps(instpkgobjs.keys())
except Exception as e:
	print e
	sys.exit(0)

for i in deps.keys():				### packages
	for j in deps[i].keys():		### requirements for package
		if deps[i][j] == []:		### no requirements
			continue

		for k in deps[i][j]:		### potential resolutions for requirements
			if instpkgobjs.get(k):
				break
		else:
			print "%s-%s-%s.%s requires one of:"%(i.name, i.version, i.release,i.arch)
			print "\t" + "\t\n".join(["%s-%s-%s.%s"%(m.name, m.version, m.release,m.arch) for m in instpkgobjs])
				
sys.exit(0)
