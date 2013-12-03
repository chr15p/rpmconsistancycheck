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
import rpmUtils.transaction
from rpmUtils.miscutils import splitFilename
from optparse import OptionParser

def parsePkgFile(filename):
	pkglist = []
	for line in open(filename):
		pkgname=line.rstrip('\n')
		if pkgname == "": continue

		if pkgname[-4:] == ".rpm":
			pkglist.append(pkgname[:-4])
		else:
			pkglist.append(pkgname)
	return pkglist


def getPkgObjs(namelist,pkgobjlist,rpmdir,ts):
	instpkgobjs = dict()
	for name in namelist:
		#print rpm
		obj = pkgobjlist.get(name,"")
		if obj =="":
			try:
				obj = yum.packages.YumLocalPackage(filename= rpmdir + "/" + name + ".rpm",ts=ts)
			except:
				print "NOT FOUND IN REPOs: " +name
				continue

		instpkgobjs[obj]=1

	return instpkgobjs


def mergeErrata(objdict, errataobj,installnew):

	erratanamedict=dict()
	for e in errataobj:
		erratanamedict[e.name]=e

	for j in objdict:
		newobj=erratanamedict.get(j.name,"")
		if newobj != "":
			if newobj.verGT(objdict[j]):
				objdict[j] = newobj
			elif newobj.verLT(objdict[j]):
				print "%s-%s-%s.%s older then installed"%(newobj.name, newobj.version, newobj.release,newobj.arch)
			elif newobj.verEQ(objdict[j]):
				print "%s-%s-%s.%s already installed"%(newobj.name, newobj.version, newobj.release,newobj.arch)
		del erratanamedict[j.name]

	if installnew:
		objdict.update(erratanamedict)



def filterNewest(objdict):
	namecache = dict()
	for e in objdict:
		name = e.name
		if namecache.get(name):
			if e.verGT(namecache[name]):
				namecache[e.name] = e
		else:
			namecache[e.name] = e

	return [(e,1) for e in namecache]


rpmlist=[]
filename=""
parser = OptionParser()
parser.add_option("-f", "--file", action="append", default=None, dest="filename", help='file containing list of package names to check')
parser.add_option("-d", "--dir", default=None, dest="dir", help='dir containing errata rpms')
parser.add_option("-r", "--repo", action="append", default=None, dest="repolist", help='id of a repo to check against')
parser.add_option("-i", "--install", default=None, action="store_const",const=1, dest="installnew", help='install errata packages not already installed')
parser.add_option("-n", "--newest", default=None, action="store_const",const=1, dest="newest", help='only check newest versions of packages')

(opt,args) = parser.parse_args()
filenames = opt.filename or sys.exit(1)
repolist = opt.repolist or sys.exit(1)
installnew = opt.installnew 
rpmdir = opt.dir or "."


ts = rpmUtils.transaction.initReadOnlyTransaction()
yb = yum.YumBase()
yb.setCacheDir()

conrepos=[]
for i in yb.repos.findRepos("*"):
	conrepos.append(i.getAttribute("id"))

yb.repos.disableRepo('*')

for repo in repolist:
	if repo not in conrepos:
		newrepo = yum.yumRepo.YumRepository(repo)
		newrepo.metadata_expire = 0
		newrepo.timestamp_check = False
		yb.repos.add(newrepo)
	
	yb.repos.enableRepo(repo)

yb.pkgSack = yb.repos.populateSack(mdtype='metadata',cacheonly=1,which='enabled')

pkgobjlist=dict()
for i in yb.pkgSack:
	pkgobjlist["%s-%s-%s.%s"%(i.name, i.version, i.release,i.arch)]=i


## read the rpms from a file

rpmobjs = dict()
for filename in filenames:
	rpmlist = parsePkgFile(filename)
	mergeErrata(rpmobjs, getPkgObjs(rpmlist,pkgobjlist,rpmdir,ts), installnew)

if opt.newest:
	filterNewest(rpmobjs)

try:
	deps = yb.findDeps(rpmobjs.keys())
except Exception , e:
	print e.value
	sys.exit(0)


for i in deps.keys():				### packages
	for j in deps[i].keys():		### requirements for package
		if deps[i][j] == []:		### no requirements
			continue

		for k in deps[i][j]:		### potential resolutions for requirements
			if rpmobjs.get(k):
				break
		else:
			print "%s-%s-%s.%s requires one of:"%(i.name, i.version, i.release,i.arch)
			print "\t" + "\n\t".join(["%s-%s-%s.%s"%(m.name, m.version, m.release,m.arch) for m in deps[i][j]])
				
sys.exit(0)
