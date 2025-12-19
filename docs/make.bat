@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=source
set BUILDDIR=build
set IMAGEDIR=source\_images

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

if "%1" == "" goto help
if "%1" == "markdown" goto markdown

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:markdown
echo Building markdown files...
%SPHINXBUILD% -b markdown %SOURCEDIR% %BUILDDIR%\markdown %SPHINXOPTS% %O%
echo Copying images...
if not exist %BUILDDIR%\markdown\_images mkdir %BUILDDIR%\markdown\_images
xcopy /s /y %IMAGEDIR%\* %BUILDDIR%\markdown\_images\
echo Copying stylesheets...
if not exist %BUILDDIR%\markdown\_static mkdir %BUILDDIR%\markdown\_static
xcopy /s /y %SOURCEDIR%\_static\* %BUILDDIR%\markdown\_static\
echo Build finished. The markdown files are in %BUILDDIR%\markdown.
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd
