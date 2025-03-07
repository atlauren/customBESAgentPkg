#!/usr/bin/env python3
# --------------------------------------------------------------------------------------------------
# -- systemDivisions
# --------------------------------------------------------------------------------------------------
# Program    : systemDivisions
# To Complie : n/a
#
# Purpose    :
#
# Called By  :
# Calls      :
#
# Author     : Rusty Myers <rzm102@psu.edu>
# Based Upon :
#
# Note       :
#
# Revisions  :
#           2016-01-25 <rzm102>   Initial Version
# 			2025-02-21 <atlauren@uci.edu> python3
#
# Version    : 1.1
# --------------------------------------------------------------------------------------------------


import sys, glob, os, re, shutil, argparse, subprocess
import xml.etree.ElementTree as ET

# Names of packages to export
name = "CUSTOM"
# Set signing cert to name of certificate on system
# Print certificates in termianl: security find-identity -v -p codesigning
signing_cert = "Developer ID Installer: Company (CODE)"


# Functions to sort list of packages
# https://stackoverflow.com/questions/4623446/how-do-you-sort-files-numerically
def tryint(s):
    try:
        return int(s)
    except:
        return s


def alphanum_key(s):
    """Turn a string into a list of string and number chunks.
    "z23a" -> ["z", 23, "a"]
    """
    return [tryint(c) for c in re.split("([0-9]+)", s)]


def sort_nicely(l):
    """Sort the given list in the way that humans expect."""
    l.sort(key=alphanum_key)


# Function to sign packages
def signPackage(pkg):
    # rename unsigned package so that we can slot the signed package into place
    print("signPackage received: {0}".format(pkg))
    pkg_dir = os.path.dirname(pkg)
    pkg_base_name = os.path.basename(pkg)
    (pkg_name_no_extension, pkg_extension) = os.path.splitext(pkg_base_name)
    unsigned_pkg_path = os.path.join(
        pkg_dir, pkg_name_no_extension + "-unsigned" + pkg_extension
    )

    os.rename(os.path.abspath(pkg), os.path.abspath(unsigned_pkg_path))

    try:
        subprocess.run(
            ["/usr/bin/productsign", "--sign", signing_cert, unsigned_pkg_path, pkg],
        )
    except:

        print("Can't find Cert? Try: ")
        print(
            """\tsecurity find-identity | grep Installer: | tail -1 | awk -F\\" '{ print $2 }'"""
        )
        exit(1)
    os.remove(unsigned_pkg_path)
    # if exit_code == 1:


# Function to remove 'relocate' tags
# This forces installer to place files in correct location on disk
def derelocatePacakge(distroPath):
    # Open Distribution file passed to function
    tree = ET.parse(distroPath)
    # Get the root of the tree
    root = tree.getroot()
    # Check each child
    for child in root:
        # If it's a pkg-ref
        if child.tag == "pkg-ref":
            # Check each subtag
            for subtag in child:
                # If it's a relocate tag
                if subtag.tag == "relocate":
                    # Remove the whole child
                    root.remove(child)
    # Remove old Distribution file
    os.remove(distroPath)
    # Write new Distribution file
    tree.write(distroPath)


# Function to load the latest BESAgent Installer
def loadPackages():
    # searches for BESAgent installer packages, returns latest version if
    # multiple are found
    # Store packages in local folder
    besPkgs = []
    # Look in local folder
    source = "./"
    # check each file
    for filename in sorted(os.listdir(source)):
        # join path and filename
        p = os.path.join(source, filename)
        # check if it's a file
        if os.path.isfile(p):
            # Check if it matches BESAgent regex
            pattern = re.compile(r"^BESAgent-(\d+.\d+.\d+.\d+)-*.*pkg")
            match = pattern.search(filename)
            # If it matches, add it to the array of all packages
            if match:
                print("Found: " + str(filename))
                besPkgs.append(p)
    # If we have more than one package found, notify
    if len(besPkgs) > 1:
        print("Found more than one package, choosing latest version.")
        sort_nicely(besPkgs)
    # Return the last package found, which should be latest verison
    try:
        latest_pkg = besPkgs[-1]
    except:
        print(
            "Can't find any pacakges! Download BESAgent package from https://support.bigfix.com/bes/release/ and place next to this script."
        )
        exit(1)
    return latest_pkg


# Clean out the modified files
def clean_up(oldfilepath):
    # We're done with the default folder, so we can remove it
    if os.path.isdir(oldfilepath):
        shutil.rmtree(oldfilepath)


# Touch a file - written by mah60
def touch(path):
    basedir = os.path.dirname(path)
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    open(path, "a").close()


# Add command line arguments
parser = argparse.ArgumentParser(
    description="Build Custom BESAgent Installers.", conflict_handler="resolve"
)

# Add option for adding band
parser.add_argument(
    "--brand",
    "-b",
    dest="custom_brand",
    action="append",
    type=str,
    help="add branding text to the BESAgent pacakge",
)

# Add option for adding custom settings
parser.add_argument(
    "--settings",
    "-s",
    dest="custom_settings",
    action="store_true",
    help="add custom settings cfg to the BESAgent pacakge",
)

# Add option for specific package
parser.add_argument(
    "--package",
    "-p",
    dest="custom_pkg",
    action="append",
    type=str,
    help="specify the BESAgent pacakge to use",
)

# Parse the arguments
args = parser.parse_args()

# Check that we're on OS X
if not sys.platform.startswith("darwin"):
    print("This script currently requires it be run on macOS")
    exit(2)

# run function to get packages
if args.custom_pkg:
    default_package = args.custom_pkg[0]
    print(default_package[0:-4])
    default_folder = default_package[0:-4]
else:
    default_package = loadPackages()
    # remove .pkg from name
    default_folder = default_package[2:-4]

# Make sure our modified package folder exists
modifiedFolder = "ModifiedPackage"
if not os.path.isdir(modifiedFolder):
    # Make it if needed
    os.mkdir(modifiedFolder)

# Notify user of default package being used
print("Using Package: " + default_package)


# Make the path for the modified package destination
modifiedDest = os.path.join(modifiedFolder, default_folder)

# Print path for modified folder
# print "Modified Dest: {0}".format(modifiedDest)
# Delete old files
clean_up(modifiedDest)

# Set path to distribution file
DistroFile = os.path.join(modifiedDest, "Distribution")

print("Copying ModifiedFiles...")
# If the default folder is missing
# Default folder is the BESAgent package expanded,
# with the addition of our ModifiedFiles.
if not os.path.isdir(modifiedDest):
    # Expand default pacakge to create the default folder
    sys_cmd = "pkgutil --expand " + default_package + " " + modifiedDest
    os.system(sys_cmd)
    # Update Distribution file to remove relocate tags
    derelocatePacakge(DistroFile)
    # Set up paths to the Modified Files and their new destination in expanded package
    src = "./ModifiedFiles/"
    dest = os.path.join(modifiedDest, "besagent.pkg/Scripts/")
    # Create array of all of the modified files
    src_files = os.listdir(src)
    # For each file in the array of all modified files
    # print "Dest {0}".format(dest)
    for file_name in src_files:
        # create path with source path and file name
        full_file_name = os.path.join(src, file_name)
        # if it's a file, copy it to the default folder
        if os.path.isfile(full_file_name):
            if "clientsettings.cfg" in full_file_name:
                if args.custom_settings:
                    print("    Copying: " + str(file_name))
                    shutil.copy(full_file_name, dest)
            else:
                print("    Copying: " + str(file_name))
                shutil.copy(full_file_name, dest)

# Make dir for destination packages
finishedFolder = default_folder[0:-10] + "Finished"
if not os.path.isdir(finishedFolder):
    os.mkdir(finishedFolder)

# Print out the one we're doing
# print "{0:<40}".format(name)
# Name of temp unit folder
unit_folder = default_folder + "-" + name
# Name of unit package
unit_package = unit_folder + ".pkg"
# Copy modified package folder to temp unit folder
sys_cmd = "cp -R " + modifiedDest + " " + unit_folder
os.system(sys_cmd)

# Echo Unit Name into Brand file if requested
if args.custom_brand:
    print("Adding custom branding.")
    sys_cmd = (
        'echo "'
        + name
        + '" > '
        + os.path.join(unit_folder, "besagent.pkg/Scripts", "brand.txt")
    )
    os.system(sys_cmd)

# Flatten customized unit folder into final package
sys_cmd = "pkgutil --flatten " + unit_folder + " " + finishedFolder + "/" + unit_package
os.system(sys_cmd)
# Clean out custom folder
clean_up(unit_folder)

# Clean ourselves up
clean_up(modifiedDest)

# Uncomment to sign pacakage before finishing
signPackage(finishedFolder + "/" + unit_package)

print("Package completed: " + str(unit_package))
