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


def getPackageList(rpmlist,pkgobjlist):
	pkgList=[]
	#print pkgobjlist
	#print rpmlist
	for i in rpmlist:
		obj = pkgobjlist.get(i,"")
		if obj != "":
			pkgList.append(obj)
		else:
			print "NOT FOUND IN REPOs: " + i

	#print pkgList
	return pkgList		



rpmlist=[]
filename=""
errval=0
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
testsack = yum.packageSack.PackageSack()

for filename in filenames:
	rpmlist = parsePkgFile(filename)
	rpmobjlist = getPackageList(rpmlist,pkgobjlist)
	for i in rpmobjlist:
		testsack.addPackage(i)

outputsack = yum.packageSack.PackageSack()
try:
	if opt.newest:
		pkgset=testsack.returnNewestByNameArch()
		deps = yb.findDeps(pkgset)
		for i in rpmobjlist:
			outputsack.addPackage(i)
	else:
		deps = yb.findDeps(testsack.returnPackages())
		outputsacksack=testsack
except Exception , e:
	print e
	sys.exit(0)


pkgs=dict()
for i in deps.keys():				### packages
	for j in deps[i].keys():		### requirements for package
		if deps[i][j] == []:		### no requirements
			continue

		for k in deps[i][j]:		### potential resolutions for requirements
			if outputsack.searchPO(k):
				break
		else:
			pkgs["%s-%s-%s.%s"%(i.name, i.version, i.release,i.arch)]=1
			print "%s-%s-%s.%s requires one of:"%(i.name, i.version, i.release,i.arch)
			print "\t" + "\n\t".join(["%s-%s-%s.%s"%(m.name, m.version, m.release,m.arch) for m in deps[i][j]])
			errval=1

if errval !=0:
	print "%s packages need attention"%(len(pkgs))
	print "\n".join(pkgs.keys())

sys.exit(errval)
