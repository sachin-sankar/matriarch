{
  pkgs ? import <nixpkgs> { },
}:

(pkgs.buildFHSEnv {
  name = "pyside-fhs-env";
  targetPkgs =
    pkgs:
    (with pkgs; [
      # Compression & Core C Libraries
      zstd # Fixes libzstd.so.1
      zlib
      glib
      openssl
      libxml2
      libxslt
      krb5
      brotli

      # GUI, Fonts & Display
      libGL
      fontconfig
      freetype
      libxkbcommon
      dbus
      wayland

      # X11 Libraries
      libX11
      libXext
      libXrender
      libXi
      libXcursor
      libXrandr
      libxcb
    ]);

  runScript = "bash";
}).env
