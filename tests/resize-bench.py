#!/usr/bin/env python

from collections import defaultdict
from optparse import OptionParser
from time import time
import logging
import os
import subprocess
import sys

from NativeImaging import get_image_class

from stats_recorder import save_to_codespeed


parser = OptionParser()
parser.add_option("-v", default=0, dest="verbosity", action="count")
parser.add_option("--codespeed-environment", default=None, help="Use a custom Codespeed environment")
parser.add_option("--codespeed-url", "--codespeed", default=None,
                    help="Save results to the specified Codespeed server")

(options, backend_names) = parser.parse_args()

if options.verbosity > 1:
    log_level = logging.DEBUG
elif options.verbosity > 0:
    log_level = logging.INFO
else:
    log_level = logging.WARNING

logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s",
                    level=log_level)

BACKENDS = {}
for backend_name in (backend_names or ('PIL', 'GraphicsMagick', 'Aware')):
    try:
        BACKENDS[backend_name] = get_image_class(backend_name)
    except KeyError:
        print >>sys.stderr, "Can't load %s backend" % backend_name

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "samples")
OUTPUT_DIR = os.path.join(os.environ.get("TMPDIR"), "resize-bench")

TIMES = defaultdict(dict)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print "Comparison images are saved in %s" % OUTPUT_DIR

for filename in os.listdir(SAMPLE_DIR):
    basename = os.path.splitext(filename)[0]

    for backend_name, backend_class in BACKENDS.items():
        logging.info("Resizing %s using %s", filename, backend_name)
        start_time = time()

        try:
            master = backend_class.open(os.path.join(SAMPLE_DIR, filename))

            master.thumbnail((256, 256), backend_class.ANTIALIAS)

            output_file = os.path.join(OUTPUT_DIR,
                                        "%s_%s.jpg" % (basename, backend_name))

            master.save(open(output_file, "wb"), "JPEG")

            TIMES[filename][backend_name] = time() - start_time

        # This allows us to use a blanket except below which has the nice
        # property of catching direct Exception subclasses and things like
        # java.lang.Exception subclasses on Jython:
        except SystemExit:
            sys.exit(1)
        except:
            logging.exception("%s: exception processing %s", backend_name,
                            filename)

print
print "Results"
print

for f_name, scores in TIMES.items():
    print "%s:" % f_name
    for lib, elapsed in scores.items():
        print "\t%16s: %0.2f" % (lib, elapsed)
    print

if options.codespeed_url:
    commit_id = subprocess.Popen(["git", "rev-parse", "HEAD"],
                                    stdout=subprocess.PIPE).communicate()[0].strip()

    for f_name, scores in TIMES.items():
        for lib, elapsed in scores.items():
            save_to_codespeed(options.codespeed_url, "NativeImaging", commit_id,
                                lib, f_name, elapsed,
                                environment=options.codespeed_environment)

