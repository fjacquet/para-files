# Homebrew formula for para-files
#
# This formula lives in the para-files repository itself.
# The url and sha256 fields are updated automatically by the release workflow
# each time a version tag is pushed.
#
# Usage:
#   brew tap fjacquet/para-files https://github.com/fjacquet/para-files
#   brew install para-files
#
# Or in one step:
#   brew install fjacquet/para-files/para-files \
#     --custom-url https://github.com/fjacquet/para-files

class ParaFiles < Formula
  include Language::Python::Virtualenv

  desc "Intelligent file classification using MLX-powered semantic routing (PARA method)"
  homepage "https://github.com/fjacquet/para-files"
  url "PLACEHOLDER"
  sha256 "PLACEHOLDER"
  license "MIT"

  # macOS Apple Silicon only:
  #   - MLX requires the Apple Neural Engine
  #   - OCR uses the macOS Vision framework (no Linux equivalent)
  depends_on :macos
  depends_on arch: :arm64

  depends_on "python@3.12"
  depends_on "pandoc"    # document conversion
  depends_on "exiftool"  # file metadata extraction

  def install
    # Create an isolated virtualenv under libexec and install the package
    # together with all its Python dependencies from PyPI.
    venv = virtualenv_create(libexec, "python@3.12")
    venv.pip_install(buildpath)
    bin.install_symlink(libexec/"bin/para-files")
  end

  test do
    # Verify the binary runs and prints a valid semver string.
    assert_match(/\d+\.\d+\.\d+/, shell_output("#{bin}/para-files --version"))
  end
end
