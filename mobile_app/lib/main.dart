import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MaterialApp(
    home: ComplaintForm(),
    debugShowCheckedModeBanner: false,
  ));
}

class ComplaintForm extends StatefulWidget {
  const ComplaintForm({super.key});

  @override
  State<ComplaintForm> createState() => _ComplaintFormState();
}

class _ComplaintFormState extends State<ComplaintForm> {
  final _formKey = GlobalKey<FormState>();
  File? _image;
  String _barcode = "Scanner un produit";
  final TextEditingController _fournisseurCtrl = TextEditingController();
  final TextEditingController _lotCtrl = TextEditingController();
  final TextEditingController _qteCtrl = TextEditingController();
  final TextEditingController _commentCtrl = TextEditingController();
  String _motif = "Manquant";

  final List<String> _motifs = ["Manquant", "Cassé", "Périmé", "Erreur Prix", "Vignette"];

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.camera);
    if (pickedFile != null) {
      setState(() => _image = File(pickedFile.path));
    }
  }

  void _scanBarcode() {
    showModalBottomSheet(
      context: context,
      builder: (context) => MobileScanner(
        onDetect: (capture) {
          final List<Barcode> barcodes = capture.barcodes;
          if (barcodes.isNotEmpty) {
            setState(() => _barcode = barcodes.first.rawValue ?? "Inconnu");
            Navigator.pop(context);
          }
        },
      ),
    );
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;

    // TODO: Remplacez par l'URL de votre application déployée
    var request = http.MultipartRequest('POST', Uri.parse('https://pharmaciel-1.onrender.com/upload_reclam'));
    request.fields['fournisseur'] = _fournisseurCtrl.text;
    request.fields['barcode'] = _barcode;
    request.fields['lot'] = _lotCtrl.text;
    request.fields['quantite'] = _qteCtrl.text;
    request.fields['motif'] = _motif;
    request.fields['commentaire'] = _commentCtrl.text;

    if (_image != null) {
      request.files.add(await http.MultipartFile.fromPath('photo', _image!.path));
    }

    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Envoi en cours...")));
    
    try {
      var response = await request.send();
      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("✅ Réclamation Envoyée !")));
        _formKey.currentState!.reset();
        setState(() {
          _image = null;
          _barcode = "Scanner un produit";
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("❌ Erreur lors de l'envoi")));
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Erreur: $e")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("DARPHARM - Nouveau Litige"),
        backgroundColor: Colors.blueAccent,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.qr_code_scanner, size: 40, color: Colors.blue),
                      const SizedBox(width: 15),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text("Code-Barres Scanné", style: TextStyle(color: Colors.grey)),
                            Text(_barcode, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                          ],
                        ),
                      ),
                      IconButton(onPressed: _scanBarcode, icon: const Icon(Icons.refresh))
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              TextFormField(controller: _fournisseurCtrl, decoration: const InputDecoration(labelText: "Fournisseur", border: OutlineInputBorder())),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: TextFormField(controller: _lotCtrl, decoration: const InputDecoration(labelText: "N° Lot", border: OutlineInputBorder()))),
                  const SizedBox(width: 10),
                  Expanded(child: TextFormField(controller: _qteCtrl, decoration: const InputDecoration(labelText: "Quantité", border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                ],
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField(
                value: _motif,
                items: _motifs.map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
                onChanged: (val) => setState(() => _motif = val as String),
                decoration: const InputDecoration(labelText: "Motif", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 10),
              TextFormField(controller: _commentCtrl, decoration: const InputDecoration(labelText: "Observations", border: OutlineInputBorder()), maxLines: 3),
              const SizedBox(height: 20),
              _image == null 
                ? Container(height: 150, width: double.infinity, color: Colors.grey.shade200, child: const Icon(Icons.camera_alt, size: 50, color: Colors.grey))
                : Image.file(_image!, height: 200, width: double.infinity, fit: BoxFit.cover),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _pickImage,
                icon: const Icon(Icons.camera_alt),
                label: const Text("PRENDRE PHOTO PREUVE"),
                style: ElevatedButton.styleFrom(minimumSize: const Size(double.infinity, 45)),
              ),
              const SizedBox(height: 30),
              SizedBox(
                width: double.infinity,
                height: 55,
                child: ElevatedButton(
                  onPressed: _submitForm,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white),
                  child: const Text("TRANSMETTRE AU SIÈGE", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
