using System.Collections.Generic;

namespace NewHireCompanyManager.Models
{
    public class Company
    {
        public Company()
        {
            Modules = new List<CompanyModule>();
        }

        public string CompanyIdentifier { get; set; }
        public string CompanyName { get; set; }
        public string Address1 { get; set; }
        public string Address2 { get; set; }
        public string City { get; set; }
        public string State { get; set; }
        public string Zip { get; set; }
        public string PhoneNumber { get; set; }
        public string PrimaryContact { get; set; }
        public string PointOfContactEmail { get; set; }
        public string TaxId { get; set; }
        public string BankName { get; set; }
        public bool Form1099 { get; set; }
        public string WithholdingNumber { get; set; }
        public string County { get; set; }
        public string LogoFileName { get; set; }
        public string LogoContentType { get; set; }
        public byte[] LogoBytes { get; set; }
        public IList<CompanyModule> Modules { get; set; }
    }
}
