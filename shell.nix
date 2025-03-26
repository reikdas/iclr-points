{
  pkgs ? import <nixpkgs> { },
}:
pkgs.mkShell {
  buildInputs = [
    (pkgs.python311.withPackages (
      ps: with ps; [
        numpy
        certifi
        charset-normalizer
        idna
        lxml
        requests
        urllib3
        xmltodict
        setuptools
        unidecode
        selenium
        webdriver-manager
        pandas
      ]
    ))
  ];
}
