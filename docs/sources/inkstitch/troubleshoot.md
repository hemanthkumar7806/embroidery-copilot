# Troubleshoot - Ink/Stitch

- **Source:** https://inkstitch.org/docs/troubleshoot
- **Collected:** 2026-02-20

**Summary:** Describes the Troubleshoot extension: Troubleshoot Objects (errors/warnings with suggested fixes), Element Info, Remove embroidery settings, Cleanup Document, and Update Ink/Stitch SVG. Use these to find and fix design issues before export.

---

# Content from https://inkstitch.org/docs/troubleshoot

Troubleshoot - Ink/Stitch

## Troubleshoot Objects

Ink/Stitch sometimes can be confusing. Especially for beginners. But also if you are using Ink/Stitch for a while, you will receive error messages, indicating that something went wrong and your shape cannot be rendered for whatever reason.

Ink/Stitch comes with an troubleshoot extension, which is designed to help you to understand the error while pointing you to the exact position were the problem lies. It will suggest how to resolve each kind of error and gives helpful tips for shapes that have issues, even if they won't cause Ink/Stitch to error out.

### Usage

- Run`Extensions > Ink/Stitch > Troubleshoot > Troubleshoot Objects`
- (Optional) Select objects that you want to test. If you select none, the whole document will be tested.
- Update Ink/Stitch svg

This feature will be part of an upcoming Ink/Stitch release. It is not yet integrated in Ink/Stitch.

- Chose what you want to detect among errors, warnings and object type warning.

You will either get a message, that no error could be found or a new layer with the troubleshoot information will be added to your SVG document. Use the objects panel (Ctrl + Shift + O) to delete the layer once you are finished.

Tip: It is possible that one object contains more than one error. Fill shapes only display the first error that will appear. Run the extension again, if you are receiving more error messages.

## Element Info

This extension informs about various parameters of selected stitch elements.

This feature will be part of an upcoming Ink/Stitch release. It is not yet integrated in Ink/Stitch.

The 'Copy' button on the help tab allows you to copy all the information to the clipboard.

## Remove embroidery settings

Use this function to remove the information Ink/Stitch has stored in your document. This can be especially useful if you copy and paste objects from an embroidery design into another document.

The extensions will remove embroidery settings from your entire design or from selected objects:

- Select one or all of the given options and click apply
- Run`Extensions > Ink/Stitch > Troubleshoot > Remove embroidery settings...`
- select objects (skip this step if you want to clear all embroidery information)

### Options

- Remove print settings from SVG metadata
- Remove commands (all/none/specific command only)
- Remove params

## Cleanup Document

Sometimes you will find very small shapes and leftover objects from various operations during your designing process in your SVG file. Ink/Stitch offers a function to clean up your document and prevent those objects from causing trouble.

- Check test run option to display names of the elements that will be removed with the current settings without actually removing anything
- You may also choose to additionnaly delete empty groups or layers
- Click apply
- Choose which types of objects should be removed and define a threshold
- Run`Extensions > Ink/Stitch > Troubleshoot > Cleanup Document...`

## Update Ink/Stitch svg

A file which was created with an older version of Ink/Stitch will automatically update.

However, if a file is already marked as updated, it will not be checked again for old elements. If design elements are copied or imported from an old file into a new file, it is possible that some parameters are no longer recognized correctly.

In this case, a manual update can be performed for individual elements:

- Run`Extensions > Ink/Stitch > Troubleshoot > Update Ink/Stitch SVG`
- Select items to update

Tip: This operation becomes superfluous if an Ink/Stitch function was previously executed in the source file of the (to be copied) design elements. To do this, simply select an item in the old file, open the params dialog and click 'Apply and Close' without any changes.
