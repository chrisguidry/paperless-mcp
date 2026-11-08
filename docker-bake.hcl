# The OCI keys of every image this repository publishes. CI fills the
# variables from the commit it builds, and `docker buildx bake --push`
# writes each key as a config label and as an annotation on the image
# index and each image manifest. The keys live here and not in the
# Dockerfile, so a change to a key invalidates no layer cache, and a
# fork that builds the Dockerfile on its own does not claim to be this
# repository's image.

# SOURCE is the repository's URL, REVISION the commit, VERSION the
# release or development version, and CREATED the commit's committer
# time in RFC 3339. A local build leaves them empty, and an empty key
# is left out.
variable "SOURCE" { default = "" }
variable "REVISION" { default = "" }
variable "VERSION" { default = "" }
variable "CREATED" { default = "" }

# The keys that are the same for every image of the repository.
variable "URL" { default = "https://github.com/chrisguidry/paperless-mcp" }
variable "LICENSES" { default = "MIT" }
variable "VENDOR" { default = "Chris Guidry" }

# oci returns the keys of one image: the commit's keys, the
# repository's keys, and the image's own keys, with the image's keys
# last so that they win. A commit key that is empty is left out, so a
# local build writes no source, revision, version, or created. Any
# other key that is "" is written as "", which replaces a label of the
# same key that the base image set.
function "oci" {
  params = [image]
  result = { for key, value in merge(
    { for key, value in {
      source   = SOURCE
      revision = REVISION
      version  = VERSION
      created  = CREATED
    } : key => value if value != "" },
    {
      url      = URL
      licenses = LICENSES
      vendor   = VENDOR
    },
    image,
  ) : "org.opencontainers.image.${key}" => value }
}

# oci_labels and oci_annotations write the keys of oci at the two
# places that readers look: the config, which docker inspect, syft,
# and Trivy read, and the index and manifests, which ghcr.io reads for
# a multi-platform image. A label passes into every image built FROM
# this one and an annotation does not, so a downstream image keeps
# none of these annotations.
function "oci_labels" {
  params = [image]
  result = oci(image)
}

# A local build with --load exports no image index, and BuildKit refuses
# an index annotation there, so only a CI build, which sets REVISION,
# writes annotations.
function "oci_annotations" {
  params = [image]
  result = REVISION == "" ? [] : [for key, value in oci(image) : "index,manifest:${key}=${value}"]
}

variable "paperless-mcp" {
  default = {
    title         = "paperless-mcp"
    description   = "A read-only MCP server for a paperless-ngx document archive, served over HTTP on port 9000"
    documentation = "https://github.com/chrisguidry/paperless-mcp#readme"
  }
}

group "default" {
  targets = ["paperless-mcp"]
}

# CI, which sets REVISION, also writes the SBOM and the maximum-detail
# provenance attestations and shares the GitHub Actions layer cache. The
# docker driver of a local build supports neither.
target "paperless-mcp" {
  context = "."
  tags = VERSION == "" ? ["ghcr.io/chrisguidry/paperless-mcp:dev"] : [
    "ghcr.io/chrisguidry/paperless-mcp:${VERSION}",
    "ghcr.io/chrisguidry/paperless-mcp:latest",
  ]
  platforms = ["linux/amd64"]
  labels = oci_labels(paperless-mcp)
  annotations = oci_annotations(paperless-mcp)
  attest = REVISION == "" ? [] : ["type=provenance,mode=max", "type=sbom"]
  cache-from = REVISION == "" ? [] : ["type=gha"]
  cache-to = REVISION == "" ? [] : ["type=gha,mode=max"]
}
